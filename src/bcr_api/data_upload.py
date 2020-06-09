"""Module for uploading custom content"""

import logging

from requests import get, post

from .bwproject import BWProject
from .validation import JSONDict, UploadCollection

logger = logging.getLogger(__name__)


class DataUploadAPI:
    """Class for working with Data Upload API.

    The Data Upload endpoint enables the uploading of documents for analysis in the Brandwatch Consumer Research Platform.
    Users have uploaded survey responses, proprietary content, and other types of data not available in the Brandwatch data library.

    # Example Usage

    ```python
    >>> from bcr_api.bwproject import BWProject,
    >>> from bcr_api.data_upload import DataUploadAPi
    >>> from bcr_api.validation import UploadCollection
    >>> project = project = BWProject(project="test_project", token="test-token-00000", username="test_username@brandwatch.com")
    >>> upload_client = DataUploadAPI(project)
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
    >>> data = UploadCollection(items=items)
    >>> upload_client.upload(data)
    ```
    """

    def __init__(self, project: BWProject) -> None:
        self.project = project
        self.TEMPLATE = project.apiurl + "content/sources"

    def upload(
        self, content_type_id: int, items: UploadCollection, request_usage: bool = False
    ) -> JSONDict:
        """Upload collection of custom content to Brandwatch platform.

        If greater than 1000 items passed, reverts to batch upload.
        # Arguments
            document_type: Integer, The id of the document type to which the uploading docs will belong.
            items: validated UploadCollection.
            requestUsage: Bool, return usage information.
        """
        if len(items) > 1000:
            logger.info("More than 1000 items found.  Uploading in batches of 1000.")
            return self.batch_upload(
                content_type_id, items=items, request_usage=request_usage
            )

        return self.project.bare_request(
            post,
            self.TEMPLATE,
            address_suffix="",
            data={
                "contentSource": content_type_id,
                "items": items.dict(skip_defaults=True),
                "requestUsage": request_usage,
            },
        )

    def batch_upload(
        self, content_type_id: int, items: UploadCollection, request_usage: bool = False
    ) -> JSONDict:
        """Batch upload collection of custom content to Brandwatch platform in groups of 1000.

        # Arguments
            content_type_id: Integer, The id of the document type to which the uploading docs will belong.
            items: validated UploadCollection.
            requestUsage: Bool, return usage information.

        """
        batch_responses = {}
        for batch_num, batch in enumerate(
            [items[i : i + 1000] for i in range(0, len(items), 1000)]
        ):
            response = self.upload(content_type_id, batch, request_usage)
            logger.info(f"Uploaded batch number: {batch_num}")
            batch_responses[f"Batch {batch_num}"] = response
        return batch_responses

    def create_content_source(self, content_type: JSONDict) -> JSONDict:
        """Content Source creation.

        Example content_type:
        ```python
        {
            "name": "Customer_Surveys",
            "description": "Customer Survey, May 2019"
        }
        ```
        """
        return self.project.bare_request(
            post, self.TEMPLATE, address_suffix="", data=content_type
        )

    def list_content_sources(self) -> JSONDict:
        """
        Content Source list.

        """
        return self.project.bare_request(get, self.TEMPLATE, address_suffix="")
