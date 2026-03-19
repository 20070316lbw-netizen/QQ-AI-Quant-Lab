## 2024-05-14 - Interactive Elements using div/span Tags Lack Keyboard Accessibility
**Learning:** Found custom UI actions built using `div` elements (like `.slicer-tool` in the sidebar) that used `onclick` without matching keyboard support. This made key features completely inaccessible to keyboard-only and screen reader users.
**Action:** Always verify that interactive custom components have `role="button"`, `tabindex="0"`, an `onkeydown` handler for Enter/Space, `aria-label`, and a clear `:focus-visible` CSS state. Where possible, use native `<button>` tags instead to get this functionality out-of-the-box.

## 2024-05-20 - Label Association with Inputs Missing in Forms
**Learning:** Found multiple `<label>` tags in `src/dashboard/templates/index.html` missing `for` attributes connecting them to their respective `<select>` and `<input>` elements. Without this, users cannot click the label to focus the input, and screen readers lack proper context when reading the input fields. Additionally, the labels lacked a `cursor: pointer` style, meaning sighted users had no visual cue that clicking the label would work.
**Action:** Always ensure that every `<label>` is explicitly associated with its form control using the `for` attribute (matching the target element's `id`). When building custom forms, add `cursor: pointer` to labels to improve interaction affordance.
