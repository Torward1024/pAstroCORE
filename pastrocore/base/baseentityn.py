import numpy as np
from typing import Any, get_origin, get_args
from common.base.baseentity import BaseEntity

class BaseEntityN(BaseEntity):
    """Entity with numpy array validation support."""

    def _validate_type(self, key: str, value: Any, expected_type: Any) -> None:
        """Validate that a value matches the expected type, including numpy arrays.

        Args:
            key (str): The attribute name being validated.
            value (Any): The value to check.
            expected_type (Any): The expected type from type annotations.

        Raises:
            TypeError: If the value does not match the expected type and is not None.
        """
        if key in ('name', 'value') and value is None:
            raise TypeError(f"Attribute '{key}' cannot be None")
        if value is None:
            return
        
        if value is None:
            return

        from typing import Union, Dict, List

        resolved_type = self._resolve_type(expected_type)
        if resolved_type is Any:
            return

        base_type = get_origin(resolved_type) or resolved_type
        type_args = get_args(resolved_type)

        if base_type is Union:
            for union_type in type_args:
                resolved_union_type = self._resolve_type(union_type)
                if resolved_union_type is type(None):
                    continue
                try:
                    self._validate_type(key, value, resolved_union_type)
                    return
                except TypeError:
                    continue
            raise TypeError(f"Attribute '{key}' does not match any type in {resolved_type}, got {type(value)}")

        if base_type in (dict, Dict):
            if not isinstance(value, dict):
                raise TypeError(f"Attribute '{key}' must be a dict, got {type(value)}")
            if type_args:
                key_type, value_type = type_args
                resolved_key_type = self._resolve_type(key_type)
                resolved_value_type = self._resolve_type(value_type)
                if resolved_value_type is Any:
                    return
                value_type_origin = get_origin(resolved_value_type)
                value_type_args = get_args(resolved_value_type)
                for k, v in value.items():
                    if not isinstance(k, resolved_key_type):
                        raise TypeError(f"Key in '{key}' must be {resolved_key_type}, got {type(k)}")
                    if v is None:
                        continue
                    if value_type_origin is Union:
                        valid = False
                        for union_type in value_type_args:
                            resolved_union_type = self._resolve_type(union_type)
                            if isinstance(v, resolved_union_type):
                                valid = True
                                break
                        if not valid:
                            raise TypeError(f"Value in '{key}' must match one of {value_type_args}, got {type(v)}")
                    elif resolved_value_type == np.ndarray:
                        if not isinstance(v, np.ndarray):
                            raise TypeError(f"Value in '{key}' must be {resolved_value_type}, got {type(v)}")
                    elif value_type_origin is List:
                        if not isinstance(v, list):
                            raise TypeError(f"Value in '{key}' must be a list, got {type(v)}")
                        list_item_type = self._resolve_type(value_type_args[0]) if value_type_args else Any
                        for item in v:
                            if item is None:
                                continue
                            if list_item_type is not Any and not isinstance(item, list_item_type):
                                raise TypeError(f"Item in list '{key}' must be {list_item_type}, got {type(item)}")
                    elif not isinstance(v, resolved_value_type):
                        raise TypeError(f"Value in '{key}' must be {resolved_value_type}, got {type(v)}")
        elif base_type is List:
            if not isinstance(value, list):
                raise TypeError(f"Attribute '{key}' must be a list, got {type(value)}")
            if type_args:
                item_type = self._resolve_type(type_args[0])
                if item_type is not Any:
                    for item in value:
                        if item is None:
                            continue
                        if not isinstance(item, item_type):
                            raise TypeError(f"Item in list '{key}' must be {item_type}, got {type(item)}")
        elif not isinstance(value, base_type):
            raise TypeError(f"Attribute '{key}' must be of type {resolved_type}, got {type(value)}")