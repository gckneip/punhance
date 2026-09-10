from dataclasses import dataclass, field
from typing import List, Optional

# Plain data holders mirroring HomeBank's flat .xhb XML elements. Attribute
# names match HomeBank's own (short, cryptic) names so the reader/writer can
# stay a thin, obvious transcription of the file format. No domain or Qt
# imports here - this module only knows about HomeBank's own shape.

OF_INCOME = 1 << 1  # 2
OF_SPLIT = 1 << 8  # 256


@dataclass
class HbCurrency:
    key: int
    iso: str = "BRL"
    name: str = ""
    symb: str = ""
    syprf: int = 1
    dchar: str = "."
    gchar: str = ","
    frac: int = 2
    rate: float = 1.0
    mdate: int = 0


@dataclass
class HbAccount:
    key: int
    pos: int = 1
    type: int = 1
    curr: int = 1
    name: str = ""
    number: str = ""
    bankname: str = ""
    initial: float = 0.0
    minimum: float = 0.0
    flags: int = 0


@dataclass
class HbPayee:
    key: int
    name: str = ""
    category: int = 0
    paymode: int = 0


@dataclass
class HbCategory:
    key: int
    parent: int = 0
    flags: int = 0
    name: str = ""


@dataclass
class HbFav:
    key: int
    amount: float = 0.0
    account: int = 0
    dst_account: int = 0
    paymode: int = 0
    payee: int = 0
    category: int = 0
    wording: str = ""
    tags: str = ""
    nextdate: int = 0
    every: int = 1
    unit: int = 2
    limit: int = 0
    weekend: int = 0
    gap: int = 0
    flags: int = 0
    scat: str = ""
    samt: str = ""
    smem: str = ""


@dataclass
class HbOperation:
    date: int
    amount: float = 0.0
    account: int = 0
    dst_account: int = 0
    paymode: int = 0
    st: int = 0
    flags: int = 0
    payee: int = 0
    category: int = 0
    wording: str = ""
    info: str = ""
    tags: str = ""
    kxfer: int = 0
    scat: str = ""
    samt: str = ""
    smem: str = ""

    @property
    def is_income(self) -> bool:
        return bool(self.flags & OF_INCOME)

    @property
    def split_flag_set(self) -> bool:
        return bool(self.flags & OF_SPLIT)

    @property
    def is_split(self) -> bool:
        # Trust the presence of actual split data over the flag bit - a
        # mismatch between the two is reported as a warning by the caller.
        return bool(self.scat)

    @property
    def is_transfer(self) -> bool:
        return self.dst_account not in (0, None)


@dataclass
class HbFile:
    v: str = "1.4"
    d: str = "050402"
    title: str = ""
    curr: int = 1
    currencies: List[HbCurrency] = field(default_factory=list)
    accounts: List[HbAccount] = field(default_factory=list)
    payees: List[HbPayee] = field(default_factory=list)
    categories: List[HbCategory] = field(default_factory=list)
    favs: List[HbFav] = field(default_factory=list)
    operations: List[HbOperation] = field(default_factory=list)
