import xml.etree.ElementTree as ET

from src.infrastructure.homebank.xhb_models import HbFile


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _set_attrs(el, **attrs):
    for key, value in attrs.items():
        if value is None or value == "":
            continue
        el.set(key, _fmt(value))


class XhbWriter:
    def write(self, hb_file: HbFile, path: str) -> None:
        root = ET.Element("homebank", {"v": hb_file.v, "d": hb_file.d})

        properties = ET.SubElement(root, "properties")
        _set_attrs(properties, title=hb_file.title, curr=hb_file.curr)

        for cur in hb_file.currencies:
            el = ET.SubElement(root, "cur")
            _set_attrs(
                el, key=cur.key, iso=cur.iso, name=cur.name, symb=cur.symb,
                syprf=cur.syprf, dchar=cur.dchar, gchar=cur.gchar,
                frac=cur.frac, rate=cur.rate, mdate=cur.mdate,
            )

        for acc in hb_file.accounts:
            el = ET.SubElement(root, "account")
            _set_attrs(
                el, key=acc.key, pos=acc.pos, type=acc.type, curr=acc.curr,
                name=acc.name, number=acc.number, bankname=acc.bankname,
                initial=acc.initial, minimum=acc.minimum, flags=acc.flags,
            )

        for pay in hb_file.payees:
            el = ET.SubElement(root, "pay")
            _set_attrs(el, key=pay.key, name=pay.name, category=pay.category, paymode=pay.paymode)

        for cat in hb_file.categories:
            el = ET.SubElement(root, "cat")
            _set_attrs(el, key=cat.key, parent=cat.parent, flags=cat.flags, name=cat.name)

        for fav in hb_file.favs:
            el = ET.SubElement(root, "fav")
            _set_attrs(
                el, key=fav.key, amount=fav.amount, account=fav.account,
                dst_account=fav.dst_account, paymode=fav.paymode, payee=fav.payee,
                category=fav.category, wording=fav.wording, tags=fav.tags,
                nextdate=fav.nextdate, every=fav.every, unit=fav.unit,
                limit=fav.limit, weekend=fav.weekend, gap=fav.gap, flags=fav.flags,
                scat=fav.scat, samt=fav.samt, smem=fav.smem,
            )

        for ope in hb_file.operations:
            el = ET.SubElement(root, "ope")
            _set_attrs(
                el, date=ope.date, amount=ope.amount, account=ope.account,
                dst_account=ope.dst_account, paymode=ope.paymode, st=ope.st,
                flags=ope.flags, payee=ope.payee, category=ope.category,
                wording=ope.wording, info=ope.info, tags=ope.tags,
                kxfer=ope.kxfer, scat=ope.scat, samt=ope.samt, smem=ope.smem,
            )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="")
        tree.write(path, encoding="UTF-8", xml_declaration=True)
