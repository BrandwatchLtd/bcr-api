"""Module for Data Validation Models"""

from collections import Counter
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import ftfy
import pandas as pd
import pendulum
from pendulum.exceptions import ParserError
from pydantic import BaseModel, Field, HttpUrl, NoneStr, validator

JSONDict = Dict[str, Any]


class GenderEnum(str, Enum):
    """Valid values for Gender Types"""

    M = "M"
    F = "F"


class EngagementEnum(str, Enum):
    """Valid values for Engagement Types"""

    REPLY = "REPLY"
    RETWEET = "RETWEET"
    COMMENT = "COMMENT"


class Geolocation(BaseModel):
    """Validation model for geolocation data to be uploaded.

    ## Fields
        * id: Optional[str] = None
        * latitude: Optional[float] = None
        * longitude: Optional[float] = None
        * zipcode: Optional[str] = None
    """

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    id: Optional[str] = None
    zipcode: Optional[str] = None

    @validator("longitude", always=True, whole=True)
    def validate_latitude_longitude(
        cls, longitude: float, values: Dict[str, Any]
    ) -> float:
        """Check lat long are both None or both present."""
        if longitude is None:
            if values.get("latitude", None):
                # if "latitude" in values and values["latitude"] is not None:
                raise ValueError("Must specify both valid `latitude` and `longitude`")
            return longitude
        elif not values.get("latitude", None):
            raise ValueError("Must specify both valid `latitude` and `longitude`")

        else:
            return longitude

    @validator("zipcode", always=True, whole=True)
    def validate_geo(cls, zipcode: str, values: Dict[str, Any]) -> Optional[str]:
        """Check 1 of 3 identifiers is valid: 1) id, 2) zipcode, 3) lat and long"""
        if zipcode:
            return zipcode
        else:
            if not values.get("id", False) and not (
                values.get("latitude", False) or values.get("longitude", False)
            ):
                raise ValueError("Must specify zipcode, id, or latitude and longitude")
        return None


class UploadItem(BaseModel):
    """Validation model for an item of content to be uploaded.

    Checks for required fields, with valid types and formatting.

    ## Fields
        * title: str
        * url: HttpUrl
        * guid: str
        * author: str
        * language: str(max_length=2, min_length=2)
        * date: str
        * contents: str(max_length=16384)
        * geolocation: Optional[Geolocation] = None
        * custom: Optional[Dict[str, str]] = None
        * age: Optional[int] = None
        * gender: Optional[GenderEnum] = None
        * pageId: Optional[str] = None
        * parentGuid: Optional[str] = None
        * authorProfileId: Optional[str] = None
        * engagementType: Optional[EngagementEnum] = None

    ## Example Usage

    ```python
    >>> from bwpy.models import UploadItem
    >>> item_dict = {
        "date": "2010-01-26T16:14:00",
        "contents": "Example content",
        "guid": "This is my guid",
        "title": "Example Title",
        "author": "me",
        "language": "en",
        "gender": "F",
        "geolocation": {
            "id": "USA.NY"
        },
        "pageId": "This is a pageId",
        "parentGuid": "123123",
        "authorProfileId": "1234567",
        "custom": {
            "field0": "value0",
            "field1": "45.2",
            "field2": "123",
            "field3": "value3",
            "field4": "value4",
            "field5": "5_stars",
            "field6": "1200",
            "field7": "5",
            "field8": "value5",
            "field9": "value6"
        }
    }
    >>> upload_item = UploadItem(**item_dict)
    ```
    """

    title: str
    author: str
    language: str = Field(..., max_length=2, min_length=2)
    date: str
    contents: str = Field(..., max_lenth=16384)
    url: HttpUrl = None  # type: ignore
    guid: NoneStr = None
    geolocation: Optional[Geolocation] = None
    custom: Optional[Dict[str, str]] = None
    age: Optional[int] = None
    gender: Optional[GenderEnum] = None
    pageId: NoneStr = None
    parentGuid: NoneStr = None
    authorProfileId: NoneStr = None
    engagementType: Optional[EngagementEnum] = None

    class Config:
        allow_mutation = False

    @validator("guid", pre=True, always=True, whole=True)
    def validate_guid_url(cls, guid: str, values: Dict[str, Any]) -> str:
        """Validate either url or guid is present."""
        if guid:
            return guid
        elif "url" in values and values["url"]:
            return values["url"]
        else:
            raise ValueError("Must specify either valid `guid` or `url`")

    @validator("date")
    def parse_datetime(cls, value: str, values: Dict[str, Any]) -> str:
        """Validate date string using pendulum parsing followed by ISO formatting."""
        try:
            date: pendulum.DateTime = pendulum.parse(value)
        except ParserError:
            try:
                date = pendulum.from_format(value, "MM/DD/YY HH:mm")
            except Exception:
                raise ValueError(
                    f"Could not validate format '{value}'. Must be YYYY-MM-DD or iso-formatted time stamp"
                )
        return date.to_iso8601_string()

    @validator("contents")
    def fix_contents(cls, value: str) -> str:
        """Fix mojibake in contents"""
        return ftfy.fix_text(value)

    @validator("title")
    def fix_title(cls, value: str) -> str:
        """Fix mojibake in title"""
        return ftfy.fix_text(value)

    @validator("author")
    def fix_author(cls, value: str) -> str:
        """Fix mojibake in author"""
        return ftfy.fix_text(value)

    @validator("custom", whole=True)
    def validate_len_custom_fields(cls, value_dict: Dict[str, str]) -> Dict[str, str]:
        """Validate number of Custom Fields"""
        if len(value_dict) > 10:
            raise ValueError(
                f"{len(value_dict)} custom fields found. Must not exceed 10."
            )
        return value_dict

    @validator("custom", whole=True)
    def validate_custom_fields(cls, value_dict: Dict[str, str]) -> Dict[str, str]:
        """Validate Custom Field key value pairs"""
        if not all(len(key) < 100 for key in value_dict.keys()) or not all(
            len(value) < 10_000 for value in value_dict.values()
        ):
            raise ValueError(
                "Could not validate custom field keys or values. keys must be less that 100 characters. values must be less that 10,000 characters"
            )
        return value_dict

    def __hash__(self) -> int:
        return hash(self.guid)

    def __eq__(self, other: Any) -> bool:
        return isinstance(self, type(other)) and self.guid == other.guid

    def dict(self, *args: Any, **kwargs: Any) -> JSONDict:
        return super().dict(exclude_unset=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UploadItem guid='{self.guid}'>"


class UploadCollection(BaseModel):
    """Validation model for collection of items to be uploaded.

    Checks for duplicate upload items. Easily convert to/from dataframe

    ## Fields
        * items: List[UploadItem]

    ## Example Usage

    ```python
    >>> from bwpy.models import UploadItem, UploadCollection
    >>> items = [
        {
            "date": "2010-01-26T16:14:00",
            "contents": "Example content",
            "guid": "This is my guid",
            "title": "Example Title",
            "author": "me",
            "language": "en",
            "gender": "F",
            "geolocation": {
                "id": "USA.NY"
            },
            "pageId": "This is a pageId",
            "parentGuid": "123123",
            "authorProfileId": "1234567",
            "custom": {
                "field0": "value0",
                "field1": "45.2",
                "field2": "123",
                "field3": "value3",
                "field4": "value4",
                "field5": "5_stars",
                "field6": "1200",
                "field7": "5",
                "field8": "value5",
                "field9": "value6"
            }
        }
    ]
    >>> upload_collection = UploadCollection(items=items)
    ```
    """

    items: List[UploadItem]

    class Config:
        allow_mutation = False

    @validator("items", whole=True)
    def unique_item_urls(cls, items: List[UploadItem]) -> List[UploadItem]:
        """Validate items are unique"""
        if len(items) != len(set(items)):
            counts = Counter(items)
            dup_items = [tup for tup in counts.most_common() if tup[1] > 1]
            dups = [str(tup[0].guid) for tup in dup_items]
            raise ValueError(f"Duplicate item guids detected: {dups}")

        return items

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "UploadCollection":
        """Create UploadCollection from pandas DataFrame containing necessary fields

        ## Arguments:
            * df: pd.DataFrame
        """
        df = df.fillna("")
        sub_df = df[
            [
                col
                for col in df.columns
                if "geolocation" not in col and "custom" not in col
            ]
        ]
        remaining = df[
            [col for col in df.columns if "geolocation" in col or "custom" in col]
        ]
        records = sub_df.to_dict(orient="records")
        records = [{key: val for key, val in rec.items() if val} for rec in records]
        if len(remaining) > 0:
            remaining_records = remaining.to_dict(orient="records")
            for i, rec in enumerate(remaining_records):
                geo_obj = {}
                custom_obj = {}
                for key, val in rec.items():
                    if val:
                        obj, sub_val = key.split(".")
                        if obj == "geolocation":
                            geo_obj[sub_val] = val
                        else:
                            custom_obj[sub_val] = val

                if geo_obj:
                    records[i]["geolocation"] = geo_obj
                if custom_obj:
                    records[i]["custom"] = custom_obj
        return cls(items=records)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert UploadCollection to pandas Dataframe with one colume for each field"""
        return pd.json_normalize(self.dict())

    def dict(self, *args: Any, **kwargs: Any):  # type: ignore
        return [rec.dict(*args, **kwargs) for rec in self.items]

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):  # type: ignore
        for item in self.items:
            yield item

    def __getitem__(self, slice: Union[int, slice]):  # type: ignore
        items = self.items[slice]
        if isinstance(items, list):
            return UploadCollection(items=items)
        else:
            return items

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UploadCollection items=['{self.items[0].__repr__()}...]'>"
