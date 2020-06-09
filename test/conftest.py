# -*- coding: utf-8 -*-
"""Test Fixtures."""


from pathlib import Path
from typing import List

import pandas as pd
import pytest
import responses

from bcr_api.bwproject import BWProject
from bcr_api.validation import JSONDict


@pytest.fixture
def upload_items() -> List[JSONDict]:
    """Raw list of upload dictionaries"""
    return [
        {
            "title": "Example Title",
            "date": "2010-01-26T16:14:00+00:00",
            "guid": "http://www.brandwatch.com/post1",
            "author": "me",
            "url": "http://www.brandwatch.com/post1",
            "contents": "Example content",
            "language": "en",
            "gender": "M",
        },
        {
            "title": "Example Title",
            "date": "2010-01-26T16:14:00+00:00",
            "author": "me",
            "url": "http://www.brandwatch.com/post2",
            "guid": "http://www.brandwatch.com/post2",
            "contents": "Example content",
            "language": "en",
            "geolocation": {"id": "USA.NY"},
        },
        {
            "date": "2010-01-26T16:14:00+00:00",
            "contents": "Example content",
            "url": "http://www.brandwatch.com/post3",
            "guid": "http://www.brandwatch.com/post3",
            "title": "Example Title",
            "author": "me",
            "language": "en",
            "custom": {"CF1": "CF1_value", "CF2": "CF2_45.2", "CF3": "CF3_123"},
            "gender": "F",
            "pageId": "This is a pageId",
            "parentGuid": "123123",
            "authorProfileId": "1234567",
            "engagementType": "REPLY",
        },
    ]


@pytest.fixture
def upload_dataframe(upload_items: List[JSONDict]) -> pd.DataFrame:
    """Pandas dataframe of upload content"""
    return pd.json_normalize(upload_items)


@pytest.fixture
def duplicate_items(upload_items: List[JSONDict]) -> List[JSONDict]:
    """Upload items with duplicates"""
    upload_items[1]["guid"] = upload_items[0]["guid"]

    return upload_items


@pytest.fixture
def mocked_responses() -> responses.RequestsMock:
    """Return mocked HexpySession"""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.brandwatch.com/me",
            status=200,
            json={"username": "test_username@brandwatch.com"},
        )
        rsps.add(
            responses.GET,
            "https://api.brandwatch.com/projects",
            status=200,
            json={"results": [{"name": "test_project", "id": 1234567}]},
        )
        yield rsps


@pytest.fixture
def fake_project(mocked_responses: responses.RequestsMock, tmp_path: Path) -> BWProject:
    """Return fake BWProject"""
    project = BWProject(
        project="test_project",
        token="test-token-00000",
        username="test_username@brandwatch.com",
        token_path=tmp_path / "tokens.txt",
    )
    return project
