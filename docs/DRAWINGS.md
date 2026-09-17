# Design and drafting PDFs

The same Add PDFs → Prepare PDFs → Review → Save All workflow handles drafting worksheets and isometric drawings. Files remain separate. Adding a drawing does not open a separate batch dashboard or require a different preparation mode.

## What the app does

- Keeps vector geometry as vectors and raster images at their existing resolution. It does not replace a drawing with a screenshot or redraw dimensions.
- Tags supported vector painting operations as a page-level Figure. Text labels outside nested artwork retain separate text tags. One Figure can reference multiple original painting operations without changing them.
- Preserves balanced optional-content layer wrappers and layer configuration. Layered drawings are flagged to check default/hidden/print visibility and descriptions across viewers.
- Tags each supported untagged CAD Form XObject invocation as a Figure. Nested streams and their resources stay intact. The description must include the meaningful text inside the drawing, because that text is part of the Figure rather than independently tagged paragraphs.
- Provides a multi-paragraph description box when a Figure row is selected. The entered explanation is stored in the PDF structure's Alt entry and recorded in its report. The app does not invent dimensions or infer the instructor's intended solution.
- Preserves already tagged structures. Existing semantic marked content inside imported CAD artwork, unsupported XObjects, recursive artwork, or depth/resource limits are flagged for specialist repair rather than rewritten unsafely.
- Runs English OCR for raster scans. Recognized dimensions, signs, decimal points, diameter/radius symbols, tolerances, and rotated labels require human verification.
- Checks each corresponding page's vector paths and line styles, all five page boxes, rotation, effective size, UserUnit, text retention, bookmarks, and rendered pixel hashes. A mismatch rejects the candidate. Comparison rendering is bounded to 1,800 pixels and 108 dpi; it is not a guarantee for every viewer and zoom level.

## A useful drawing explanation

Identify the object and the purpose of the drawing, the view direction and which faces are visible, dimensions and units, holes/slots/fillets and their relationships, hidden or center lines, tolerances and notes, and what the student is asked to determine. Explain each separate view or diagram on the page. Include values only after checking them against the actual source. Do not reveal an assessment's intended answer accidentally when describing its prompt.

Full descriptions may need a structured companion explanation, an accessible source document, tactile material, or an instructor-provided alternative for the particular learner and teaching task. A Figure description by itself does not establish equivalent access to every spatial reasoning exercise. W3C's [complex images guidance](https://www.w3.org/WAI/tutorials/images/complex/) discusses both identification and fuller descriptions of essential information.

## Synthetic regression cases

`fixtures/isometric-vector.pdf`: two different sheets, landscape and rotated pages, thin and dashed edges, a hole ellipse, dimension labels, Unicode diameter and tolerance symbols, a distinct second view, UserUnit=2 on the first page, and an explicit trim box. This intentionally exercises unusual PDF scaling metadata; it is a software fixture, not a manufacturing drawing.

`fixtures/isometric-nested-cad.pdf`: the same content imported through nested Form XObjects, typical of CAD/PDF composition.

`fixtures/isometric-scanned.pdf`: image-only versions of the two drawing sheets, for OCR and image preservation.

The tests also introduce pre-marked nested content to verify safe deferral, preserve direct and nested optional-content CAD layers, change UserUnit and add a vector line to prove altered geometry is rejected, check multi-paragraph UI editing, verify Figure MCIDs against the ParentTree, confirm raw original operators survive tagging/review, and check the actual saved PDF's local Brightspace format result. These fixtures supplement the mixed 1/10/50/100-file batch tests; they do not represent every CAD exporter or real classroom source.
