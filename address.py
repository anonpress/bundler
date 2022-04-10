from typing import NamedTuple


class Address(NamedTuple):
    address1: str
    address2: str
    city: str
    state: str
    zip: str

    def __eq__(self, other):
        return self.address1 == other.address1 and self.address2 == other.address2 and \
               self.city == other.city and self.state == other.state and self.zip == other.zip
