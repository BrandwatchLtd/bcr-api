# -*- coding: utf-8 -*-
"""Tests for model validation."""
import logging
from typing import List

import pandas as pd
import pytest
import responses
from _pytest.capture import CaptureFixture
from _pytest.fixtures import SubRequest
from pydantic import ValidationError

from bcr_api.content_upload import ContentUploadAPI
from bcr_api.bwproject import BWProject

from bcr_api.validation import Geolocation, UploadCollection, UploadItem, JSONDict


def test_correct_upload_item(upload_items: List[JSONDict]) -> None:
    """Test valid item dictionary is accepted."""
    validated = UploadItem(**upload_items[0])
    assert validated.dict() == upload_items[0]


def test_upload_from_df(
    upload_items: List[JSONDict], upload_dataframe: pd.DataFrame
) -> None:
    """Test dataframe for upload can be validated"""

    validated = UploadCollection.from_dataframe(upload_dataframe)
    assert validated.dict() == upload_items


def test_upload_to_df(upload_dataframe: pd.DataFrame) -> None:
    """Test back and forth to dataframe is equal"""
    validated = UploadCollection.from_dataframe(upload_dataframe)
    assert upload_dataframe.equals(validated.to_dataframe()[upload_dataframe.columns])


def test_upload_iteration(upload_items: List[JSONDict]) -> None:
    """Test iteration over collection"""
    validated = UploadCollection(items=upload_items)
    for i, item in zip(range(len(validated)), validated):
        assert validated[i] == item


@pytest.fixture
def invalid_item(upload_items: List[JSONDict]) -> JSONDict:
    """Upload item with invalid values for language, date, url"""
    altered = upload_items[0]
    altered["language"] = "engl"
    altered["date"] = "02-2031-01"
    altered["url"] = "incorrect.com"
    return altered


def test_wrong_upload_item(invalid_item: JSONDict) -> None:
    """Test invalid data and error messages"""

    with pytest.raises(ValidationError) as e:
        invalid = UploadItem(**invalid_item)  # noqa: F841
    assert e.value.errors() == [
        {
            "ctx": {"limit_value": 2},
            "loc": ("language",),
            "msg": "ensure this value has at most 2 characters",
            "type": "value_error.any_str.max_length",
        },
        {
            "loc": ("date",),
            "msg": "Could not validate format '02-2031-01'. Must be YYYY-MM-DD or iso-formatted time stamp",
            "type": "value_error",
        },
        {
            "loc": ("url",),
            "msg": "invalid or missing URL scheme",
            "type": "value_error.url.scheme",
        },
    ]


@pytest.fixture
def only_url_item(upload_items: List[JSONDict]) -> JSONDict:
    """Fixture for upload item with only url field"""
    altered = upload_items[0]
    del altered["guid"]
    return altered


def test_only_url(only_url_item: JSONDict) -> None:
    """Test validation of upload items without guid"""
    validated = UploadItem(**only_url_item)
    assert validated.dict() == only_url_item


@pytest.fixture
def only_guid_item(upload_items: List[JSONDict]) -> JSONDict:
    """Fixture for upload item with only guid field"""
    altered = upload_items[0]
    del altered["url"]
    return altered


def test_only_guid(only_guid_item: JSONDict) -> None:
    """Test validation of upload item without url"""
    validated = UploadItem(**only_guid_item)
    assert validated.dict() == only_guid_item


@pytest.fixture
def no_url_or_guid_item(upload_items: List[JSONDict]) -> JSONDict:
    """Fixture for upload item with neither url or guid field"""
    altered = upload_items[0]
    altered["url"] = None
    altered["guid"] = None
    return altered


def test_missing_url_and_guid(no_url_or_guid_item: JSONDict) -> None:
    """Test validation fails for upload item without url or guid"""
    with pytest.raises(ValidationError) as e:
        invalid = UploadItem(**no_url_or_guid_item)  # noqa: F841
    assert e.value.errors() == [
        {
            "loc": ("guid",),
            "msg": "Must specify either valid `guid` or `url`",
            "type": "value_error",
        }
    ]


@pytest.fixture
def too_many_custom_fields(upload_items: List[JSONDict]) -> JSONDict:
    """Upload item with more than 10 custom fields"""
    altered = upload_items[0]
    altered["custom"] = {str(x): str(x) for x in range(15)}
    return altered


def test_too_many_custom_fields(too_many_custom_fields: JSONDict) -> None:
    """Test upload has too many custom fields"""

    with pytest.raises(ValidationError) as e:
        invalid = UploadItem(**too_many_custom_fields)  # noqa: F841

    assert e.value.errors() == [
        {
            "loc": ("custom",),
            "msg": "15 custom fields found. Must not exceed 10.",
            "type": "value_error",
        }
    ]


@pytest.fixture
def long_custom_fields(upload_items: List[JSONDict]) -> JSONDict:
    """Upload item with custom field value of length 10002 characters"""
    altered = upload_items[0]
    altered["custom"] = {"1": "a" * 10_002}
    return altered


def test_long_custom_fields(long_custom_fields: JSONDict) -> None:
    """Test custom field values are too long"""

    with pytest.raises(ValidationError) as e:
        invalid = UploadItem(**long_custom_fields)  # noqa: F841
    assert e.value.errors() == [
        {
            "loc": ("custom",),
            "msg": "Could not validate custom field keys or values. keys must be less that 100 characters. values must be less that 10,000 characters",
            "type": "value_error",
        }
    ]


def test_detect_duplicate_upload_items(duplicate_items: List[JSONDict]) -> None:
    """Test duplicate items detected"""

    with pytest.raises(ValidationError) as e:
        invalid_collection = UploadCollection(items=duplicate_items)  # noqa: F841

    assert e.value.errors() == [
        {
            "loc": ("items",),
            "msg": "Duplicate item guids detected: ['http://www.brandwatch.com/post1']",
            "type": "value_error",
        }
    ]


def test_unique_upload_items(upload_items: List[JSONDict]) -> None:
    """Test validated dict() is same as original"""
    validated = UploadCollection(items=upload_items)
    assert validated.dict() == upload_items


@pytest.fixture
def large_upload_collection(upload_items: List[JSONDict]) -> UploadCollection:
    """Collection of 3050 unique upload items"""
    items = []

    item = upload_items[0]
    for i in range(3050):
        copy = item.copy()
        copy["guid"] = copy["guid"].replace("post1", f"post{i}")
        items.append(copy)

    collection = UploadCollection(items=items)
    return collection


@responses.activate
def test_batch_upload(
    large_upload_collection: UploadCollection,
    fake_project: BWProject,
    caplog: CaptureFixture,
) -> None:
    """Test more than 1000 items are uploaded in batches"""
    responses.add(
        responses.POST, fake_project.apiurl + "content/sources", json={}, status=200
    )

    client = ContentUploadAPI(fake_project)

    with caplog.at_level(logging.INFO):
        response = client.upload(items=large_upload_collection)

        assert (
            caplog.records[0].msg
            == "More than 1000 items found.  Uploading in batches of 1000."
        )

    assert response == {"Batch 0": {}, "Batch 1": {}, "Batch 2": {}, "Batch 3": {}}


@pytest.fixture
def geo_fixture() -> JSONDict:
    """Sample geography fixture"""
    return {"id": "23452354", "latitude": None, "zipcode": ""}


def test_valid_geo(geo_fixture: JSONDict) -> None:
    """Test Geolocation validation works correctly"""
    geo = Geolocation(**geo_fixture)

    assert geo.dict() == {
        "id": "23452354",
        "latitude": None,
        "longitude": None,
        "zipcode": None,
    }


@pytest.fixture
def invalid_geo(geo_fixture: JSONDict) -> JSONDict:
    """Invalid geographry fixture"""
    geo_fixture["id"] = ""
    return geo_fixture


def test_invalid_geo(invalid_geo: JSONDict) -> None:
    """Detect when none of zipcode, id or valid coordinates are provided"""
    with pytest.raises(ValidationError) as e:
        Geolocation(**invalid_geo)

    assert e.value.errors() == [
        {
            "loc": ("zipcode",),
            "msg": "Must specify zipcode, id, or latitude and longitude",
            "type": "value_error",
        }
    ]


@pytest.fixture(params=["latitude", "longitude"])
def latitude_longitude_mismatch(geo_fixture: JSONDict, request: SubRequest) -> JSONDict:
    """Fixture for testing validation with either missing latitude or longitude"""
    if request.param == "latitude":
        geo_fixture["latitude"] = -13542.34

    else:
        geo_fixture["longitude"] = 132.3434
    return geo_fixture


def test_lat_long_mismatch(latitude_longitude_mismatch: JSONDict) -> None:
    """Test both latitude and longitude must be present"""

    with pytest.raises(ValidationError) as e:
        Geolocation(**latitude_longitude_mismatch)

    assert e.value.errors() == [
        {
            "loc": ("longitude",),
            "msg": "Must specify both valid `latitude` and `longitude`",
            "type": "value_error",
        }
    ]
