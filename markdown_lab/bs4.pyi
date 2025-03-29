from re import Pattern
from typing import Any, Callable, Dict, List, Optional, Type, Union

class Tag:
    name: str
    attrs: Dict[str, Any]
    contents: List[Any]
    string: Optional[str]
    parent: Optional["Tag"]

    def __init__(
        self,
        parser: Any = None,
        builder: Any = None,
        name: Optional[str] = None,  # noqa: ARG002
        attrs: Optional[Dict[str, Any]] = None,
        parent: Optional["Tag"] = None,  # noqa: ARG002
        previous: Optional["Tag"] = None,
        is_xml: bool = False,  # noqa: ARG002
        sourceline: Optional[int] = None,
        sourcepos: Optional[int] = None,  # noqa: ARG002
        can_be_empty_element: bool = False,
        cdata_list_attributes: Optional[List[str]] = None,  # noqa: ARG002
        preserve_whitespace_tags: Optional[List[str]] = None,
    ) -> None: ...  # noqa: ARG002
    def get(self, key: str, default: Any = None) -> Any: ...
    def find_all(
        self,
        name: Optional[Union[str, List[str], Pattern, Callable, Type]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        string: Optional[Union[str, Pattern, Callable]] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> List["Tag"]: ...
    def find(
        self,
        name: Optional[Union[str, List[str], Pattern, Callable, Type]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        string: Optional[Union[str, Pattern, Callable]] = None,
        **kwargs: Any,
    ) -> Optional["Tag"]: ...
    def get_text(
        self,
        separator: str = "",
        strip: bool = False,
        types: Optional[List[Type]] = None,
    ) -> str: ...

class NavigableString:
    string: str

    def __init__(self, value: str) -> None: ...
    def get_text(self, separator: str = "", strip: bool = False) -> str: ...

class BeautifulSoup:
    title: Optional[Tag]
    body: Optional[Tag]

    def __init__(
        self,
        markup: Union[str, bytes] = "",
        features: Optional[str] = None,
        builder: Optional[Any] = None,
        parse_only: Optional[Any] = None,
        from_encoding: Optional[str] = None,
        exclude_encodings: Optional[List[str]] = None,
        element_classes: Optional[Dict[str, Type]] = None,
        **kwargs: Any,
    ) -> None: ...
    def find(
        self,
        name: Optional[Union[str, List[str], Pattern, Callable, Type]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        string: Optional[Union[str, Pattern, Callable]] = None,
        **kwargs: Any,
    ) -> Optional[Tag]: ...
    def find_all(
        self,
        name: Optional[Union[str, List[str], Pattern, Callable, Type]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        recursive: bool = True,
        string: Optional[Union[str, Pattern, Callable]] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Tag]: ...
