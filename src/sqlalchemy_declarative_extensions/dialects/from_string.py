import enum
import functools
from typing import Iterable, List, Type, TypeVar, Union

FromStringsSelf = TypeVar("FromStringsSelf", bound="FromStrings")


@functools.total_ordering
class FromStrings(enum.Enum):
    @classmethod
    def from_strings(
        cls: Type[FromStringsSelf], strings: Iterable[Union[str, FromStringsSelf]]
    ) -> List[FromStringsSelf]:
        return [cls.from_string(string) for string in strings]

    @classmethod
    def from_string(
        cls: Type[FromStringsSelf], string: Union[str, FromStringsSelf]
    ) -> FromStringsSelf:
        """Coerce a string into a member of this enum, passing members through unchanged.

        The enum's value is matched first, case-insensitively, followed by the
        member name. The latter matters for members whose value contains a space
        (such as ``NO SQL`` or ``INSTEAD OF``), where the member name is the more
        natural thing to write.
        """
        if not isinstance(string, str):
            return string

        normalized_str = string.upper()
        for member in cls:
            if member.value == normalized_str:
                return member

        named_member = cls.__members__.get(string.lower())
        if named_member is not None:
            return named_member

        return cls(normalized_str)

    def __lt__(self, other):
        return self.value < other.value
