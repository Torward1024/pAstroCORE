# super/schedule_address.py
"""Naming a part of a project the way a person does (L4).

What a request names is the object itself, and what the journal records is its path -- the names
the model gives its parts, which for most of them are generated: `obs_5fb241a7...`,
`srcs_3bc10499...`, `scan_9167c643...`. Nobody types those. A person says `OBS001`, `sources`,
`3C273`, `ALMA`.

An address is that, separated by slashes:

    project                              the project
    OBS001                               an observation, by its code or its name
    OBS001/sources                       a part of it, by the field that holds it
    OBS001/sources/3C273                 an item, by its name
    OBS001/telescopes/ALMA               ... or by its code, where it has one
    OBS001/scans/#3                      ... or by its position, counted from 1

**Nothing here lists the model.** Which parts an observation has is read from the model graph MSB
derives from the annotations, and an item matches by the fields every item has, so a part added
to the model tomorrow is addressable without a line changing here.

Four questions, each an `inspect` handler: `locate` an address, give the `address` of an object,
list the `contents` at one, and say what a request `offers` there. A command line and a shell are
built from them; a server would be too.
"""
import difflib
from typing import Any, Dict, List, Optional

from msb_arch.base.basecontainer import BaseContainer
from msb_arch.base.baseentity import BaseEntity

#: What an address that names the project itself says.
ROOT = "project"


class AddressQuestions:
    """Addresses a person types, turned into objects and back.

    Handlers of `inspect`, inherited by `ScheduleInspector`.
    """

    # --- the four questions ----------------------------------------------------------------------

    def _inspect_locate(self, obj: Any, attributes: Dict[str, Any]) -> Any:
        """Return the object an address names.

        Args:
            obj: Ignored; an address starts at the project this orchestrator manages.
            attributes: `address`, such as `OBS001/sources/3C273`.

        Returns:
            Any: The object itself.

        Raises:
            ValueError: Naming the segment nothing matched, what is there instead, and the
                nearest spelling when one is close.
        """
        address = attributes.get("address")
        if not isinstance(address, str) or not address.strip():
            raise ValueError("No 'address' given; try 'project' or an observation's code")
        found = self._root()
        walked = []
        for segment in self._segments(address):
            children = self._children(found)
            match = self._match(children, segment)
            if match is None:
                here = "/".join(walked) or ROOT
                names = [name for name, _ in children]
                near = difflib.get_close_matches(segment, names, n=1)
                offered = ", ".join(names[:12]) + (" ..." if len(names) > 12 else "")
                raise ValueError(
                    f"Nothing called '{segment}' in {here}"
                    + (f" -- did you mean '{near[0]}'?" if near else ".")
                    + (f" There is: {offered}" if names else " It holds nothing."))
            found = match
            walked.append(segment)
        return found

    def _inspect_address(self, obj: Any, attributes: Dict[str, Any]) -> Optional[str]:
        """Return the address of an object, as a person would type it.

        Args:
            obj: The object; `object` in the attributes overrides it.
            attributes: `object`, optionally.

        Returns:
            Optional[str]: `project`, `OBS001/sources/3C273`, and so on; None for something that
                is not part of the project.

        Notes:
            - From the path MSB records, which is the ownership graph: each step that is an item
              of what holds it is named as an item, and each field of an entity by the field. A
              step the path names but nothing holds -- a project keeps its observations in a
              mapping of its own -- locates to nothing and is passed over.
        """
        target = attributes.get("object", obj)
        root = self._root()
        if target is root:
            return ROOT
        path = self._manipulator.address(target)
        if not path:
            return None
        segments = []
        parent = root
        for depth in range(1, len(path) + 1):
            step = self._manipulator.locate(path[:depth])
            if step is None or step is parent:
                continue
            named = next((name for name, child in self._children(parent) if child is step), None)
            if named is None:
                return None                     # something on the way this cannot name
            segments.append(named)
            parent = step
        return "/".join(segments) if parent is target else None

    def _inspect_contents(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List what is at an address, one level down.

        Args:
            obj: Ignored.
            attributes: `address`; the project when not given.

        Returns:
            List[Dict[str, Any]]: `{"segment", "type", "active"}` for each thing there -- the
                segment being what to type after a slash to reach it.
        """
        address = attributes.get("address") or ROOT
        at = self._inspect_locate(obj, {"address": address})
        return [{"segment": name, "type": type(child).__name__,
                 "active": getattr(child, "isactive", None)}
                for name, child in self._children(at)]

    def _inspect_offers(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Say what a request of one operation can ask of the object at an address.

        Args:
            obj: Ignored.
            attributes: `operation`; `address`, the project when not given.

        Returns:
            Dict[str, Any]: `{"handlers": {name: [keys it reads]}, "methods": [...]}` -- the
                operation's handlers, and for `inspect` and `configure` the model's own methods
                the object has: the reading ones for `inspect`, every one for `configure`.

        Raises:
            ValueError: For an operation that is not registered, naming the ones that are.
        """
        operation = attributes.get("operation")
        described = self._manipulator.describe_operations()
        if operation not in described:
            raise ValueError(f"No operation called '{operation}'; there is "
                             f"{', '.join(sorted(described))}")
        handlers = {name: list(entry.get("accepts") or [])
                    for name, entry in sorted(described[operation].items())}

        methods: List[str] = []
        if operation in self._manipulator.CALLING:
            at = self._inspect_locate(obj, {"address": attributes.get("address") or ROOT})
            offered = self._manipulator.get_methods_for_type(type(at))
            methods = sorted(name for name in offered if not name.startswith("_")
                             and (operation != "inspect" or self.reads(name)))
        return {"handlers": handlers, "methods": methods}

    # --- walking ---------------------------------------------------------------------------------

    def _root(self) -> Any:
        root = self._manipulator.get_managing_object()
        if root is None:
            raise ValueError("There is no project to address anything in")
        return root

    @staticmethod
    def _segments(address: str) -> List[str]:
        segments = [segment for segment in address.strip().split("/") if segment]
        # `project` names where every address starts, so it may be written or left out.
        return segments[1:] if segments and segments[0] == ROOT else segments

    def _children(self, obj: Any) -> List[tuple]:
        """Return `(segment, object)` for everything one step below an object.

        Notes:
            - A container, or a project, holds items: each is named by its `code` when it has
              one, which is what a person uses for an observation or a station, and by its name
              otherwise.
            - An entity holds what its annotations say it holds, read from MSB's model graph --
              for an observation, its sources, telescopes, scans and frequencies.
        """
        if isinstance(obj, BaseContainer) or hasattr(obj, "get_observations"):
            return [(self._item_segment(item), item) for item in obj.get_items()]
        if isinstance(obj, BaseEntity):
            graph = self._manipulator.describe_model().get(type(obj).__name__, {})
            children = []
            for field in graph.get("holds", {}):
                value = getattr(obj, field, None)
                if isinstance(value, (BaseContainer, BaseEntity)):
                    children.append((field, value))
            return children
        return []

    @staticmethod
    def _item_segment(item: Any) -> str:
        code = item.get("code") if item.has_attribute("code") else None
        return str(code) if code else str(item.name)

    @staticmethod
    def _match(children: List[tuple], segment: str) -> Any:
        """Return the child a segment names: by what it is listed as, its name, or `#N`."""
        for name, child in children:
            if segment == name or segment == getattr(child, "name", None):
                return child
        if segment.startswith("#") and segment[1:].isdigit():
            position = int(segment[1:])
            if 1 <= position <= len(children):
                return children[position - 1][1]
        return None
