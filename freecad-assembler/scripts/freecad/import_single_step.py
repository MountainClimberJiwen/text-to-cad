# -*- coding: utf-8 -*-
import os
import sys

import FreeCAD as App

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from step_importer import get_step_summary, import_step_feature


def main():
    step_path = os.environ.get("STEP_PATH")
    if not step_path:
        raise SystemExit("Usage: STEP_PATH=/abs/path/to/file.step [DOC_NAME=ImportedStep] FreeCADCmd import_single_step.py")

    step_path = os.path.abspath(step_path)
    doc_name = os.environ.get("DOC_NAME", "ImportedStep")
    output_path = os.path.join(os.path.dirname(step_path), f"{doc_name}.FCStd")

    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)

    obj_name = os.path.splitext(os.path.basename(step_path))[0].replace(" ", "_")
    obj = import_step_feature(doc, obj_name, step_path, 0, 0, 0)
    doc.recompute()
    doc.saveAs(output_path)

    print("Imported STEP:", step_path)
    print("Saved FCStd:", output_path)
    print("Object:", obj.Name)
    print("Summary:", get_step_summary(step_path))


if __name__ == "__main__":
    main()
