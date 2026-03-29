from __future__ import annotations

import xml.etree.ElementTree as ET

from scripts.services.fetch_excel_from_smb import NS, _patch_app_properties, _patch_workbook_xml


def test_patch_app_properties_syncs_sheet_titles_and_count() -> None:
    app_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Sheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>3</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="3" baseType="lpstr">
      <vt:lpstr>Sheet A</vt:lpstr>
      <vt:lpstr>Sheet B</vt:lpstr>
      <vt:lpstr>Sheet C</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
</Properties>
"""

    patched = _patch_app_properties(app_xml, ["Sheet A", "Sheet C"])
    root = ET.fromstring(patched)

    vector_el = root.find("ep:TitlesOfParts/vt:vector", NS)
    assert vector_el is not None
    assert vector_el.get("size") == "2"
    assert [el.text for el in vector_el.findall("vt:lpstr", NS)] == ["Sheet A", "Sheet C"]

    count_el = root.find("ep:HeadingPairs/vt:vector/vt:variant[2]/vt:i4", NS)
    assert count_el is not None
    assert count_el.text == "2"


def test_patch_workbook_xml_updates_view_indices_after_sheet_removal() -> None:
    workbook_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <bookViews>
    <workbookView firstSheet="3" activeTab="4" />
  </bookViews>
  <sheets>
    <sheet name="Sheet A" sheetId="1" r:id="rId1" />
    <sheet name="Sheet B" sheetId="2" r:id="rId2" />
    <sheet name="Sheet C" sheetId="3" r:id="rId3" />
    <sheet name="Sheet D" sheetId="4" r:id="rId4" />
    <sheet name="Sheet E" sheetId="5" r:id="rId5" />
  </sheets>
  <customWorkbookViews>
    <customWorkbookView name="View 1" activeSheetId="4" />
  </customWorkbookViews>
</workbook>
"""

    patched = _patch_workbook_xml(workbook_xml, {"Sheet B"}, {1})
    root = ET.fromstring(patched)

    workbook_view = root.find("ss:bookViews/ss:workbookView", NS)
    assert workbook_view is not None
    assert workbook_view.get("firstSheet") == "2"
    assert workbook_view.get("activeTab") == "3"

    custom_view = root.find("ss:customWorkbookViews/ss:customWorkbookView", NS)
    assert custom_view is not None
    assert custom_view.get("activeSheetId") == "3"
