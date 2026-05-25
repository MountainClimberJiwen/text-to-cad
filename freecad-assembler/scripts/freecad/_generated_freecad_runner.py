# -*- coding: utf-8 -*-
import os
import sys
import traceback

import FreeCAD as App
import Import


GENERATED_SCRIPT_PATH = os.environ["GENERATED_SCRIPT_PATH"]
OUTPUT_STEP_PATH = os.environ["OUTPUT_STEP_PATH"]
OUTPUT_FCSTD_PATH = os.environ["OUTPUT_FCSTD_PATH"]


def close_all_documents():
    for name in list(App.listDocuments().keys()):
        App.closeDocument(name)


def get_exportable_objects(document):
    exportable = []
    for obj in document.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        try:
            if shape.isNull():
                continue
        except Exception:
            continue
        exportable.append(obj)
    return exportable


def main():
    close_all_documents()
    script_dir = os.path.dirname(GENERATED_SCRIPT_PATH)
    if script_dir and script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    os.chdir(script_dir or os.getcwd())

    namespace = {
        "__name__": "__main__",
        "__file__": GENERATED_SCRIPT_PATH,
    }
    with open(GENERATED_SCRIPT_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    exec(compile(source, GENERATED_SCRIPT_PATH, "exec"), namespace, namespace)

    document = App.ActiveDocument
    if document is None:
        docs = App.listDocuments()
        if docs:
            document = docs[list(docs.keys())[-1]]
    if document is None:
        raise RuntimeError("Generated script did not create a FreeCAD document.")

    document.recompute()
    os.makedirs(os.path.dirname(OUTPUT_FCSTD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_STEP_PATH), exist_ok=True)
    document.saveAs(OUTPUT_FCSTD_PATH)

    exportable = get_exportable_objects(document)
    if not exportable:
        raise RuntimeError("Generated document has no exportable shapes.")
    Import.export(exportable, OUTPUT_STEP_PATH)

    print("RUNNER_OK")
    print("ACTIVE_DOC", document.Name)
    print("FCSTD_PATH", OUTPUT_FCSTD_PATH)
    print("STEP_PATH", OUTPUT_STEP_PATH)
    print("EXPORTED_COUNT", len(exportable))


try:
    main()
except Exception as error:
    print("RUNNER_ERROR", str(error))
    traceback.print_exc()
    raise
