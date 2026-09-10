import xml.etree.ElementTree as ET

from src.infrastructure.homebank.xhb_models import (
    HbAccount, HbCategory, HbCurrency, HbFav, HbFile, HbOperation, HbPayee,
)


class XhbParseError(ValueError):
    pass


def _int(el, name, default=0):
    raw = el.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _float(el, name, default=0.0):
    raw = el.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _str(el, name, default=""):
    return el.get(name, default) or default


class XhbReader:
    def parse(self, path: str) -> HbFile:
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise XhbParseError(f"Malformed XML in {path}: {exc}") from exc
        except OSError as exc:
            raise XhbParseError(f"Could not read {path}: {exc}") from exc

        root = tree.getroot()
        if root.tag != "homebank":
            raise XhbParseError(
                f"Not a HomeBank file: expected root <homebank>, found <{root.tag}>"
            )

        hb_file = HbFile(
            v=root.get("v", "1.4"),
            d=root.get("d", "050402"),
        )

        properties = root.find("properties")
        if properties is not None:
            hb_file.title = _str(properties, "title")
            hb_file.curr = _int(properties, "curr", 1)

        for el in root.findall("cur"):
            hb_file.currencies.append(HbCurrency(
                key=_int(el, "key"),
                iso=_str(el, "iso", "BRL"),
                name=_str(el, "name"),
                symb=_str(el, "symb"),
                syprf=_int(el, "syprf", 1),
                dchar=_str(el, "dchar", "."),
                gchar=_str(el, "gchar", ","),
                frac=_int(el, "frac", 2),
                rate=_float(el, "rate", 1.0),
                mdate=_int(el, "mdate"),
            ))

        for el in root.findall("account"):
            hb_file.accounts.append(HbAccount(
                key=_int(el, "key"),
                pos=_int(el, "pos", 1),
                type=_int(el, "type", 1),
                curr=_int(el, "curr", 1),
                name=_str(el, "name"),
                number=_str(el, "number"),
                bankname=_str(el, "bankname"),
                initial=_float(el, "initial"),
                minimum=_float(el, "minimum"),
                flags=_int(el, "flags"),
            ))

        for el in root.findall("pay"):
            hb_file.payees.append(HbPayee(
                key=_int(el, "key"),
                name=_str(el, "name"),
                category=_int(el, "category"),
                paymode=_int(el, "paymode"),
            ))

        for el in root.findall("cat"):
            hb_file.categories.append(HbCategory(
                key=_int(el, "key"),
                parent=_int(el, "parent"),
                flags=_int(el, "flags"),
                name=_str(el, "name"),
            ))

        for el in root.findall("fav"):
            hb_file.favs.append(HbFav(
                key=_int(el, "key"),
                amount=_float(el, "amount"),
                account=_int(el, "account"),
                dst_account=_int(el, "dst_account"),
                paymode=_int(el, "paymode"),
                payee=_int(el, "payee"),
                category=_int(el, "category"),
                wording=_str(el, "wording"),
                tags=_str(el, "tags"),
                nextdate=_int(el, "nextdate"),
                every=_int(el, "every", 1),
                unit=_int(el, "unit", 2),
                limit=_int(el, "limit"),
                weekend=_int(el, "weekend"),
                gap=_int(el, "gap"),
                flags=_int(el, "flags"),
                scat=_str(el, "scat"),
                samt=_str(el, "samt"),
                smem=_str(el, "smem"),
            ))

        for el in root.findall("ope"):
            hb_file.operations.append(HbOperation(
                date=_int(el, "date"),
                amount=_float(el, "amount"),
                account=_int(el, "account"),
                dst_account=_int(el, "dst_account"),
                paymode=_int(el, "paymode"),
                st=_int(el, "st"),
                flags=_int(el, "flags"),
                payee=_int(el, "payee"),
                category=_int(el, "category"),
                wording=_str(el, "wording"),
                info=_str(el, "info"),
                tags=_str(el, "tags"),
                kxfer=_int(el, "kxfer"),
                scat=_str(el, "scat"),
                samt=_str(el, "samt"),
                smem=_str(el, "smem"),
            ))

        return hb_file
