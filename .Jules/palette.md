## 2024-05-14 - Interactive Elements using div/span Tags Lack Keyboard Accessibility
**Learning:** Found custom UI actions built using `div` elements (like `.slicer-tool` in the sidebar) that used `onclick` without matching keyboard support. This made key features completely inaccessible to keyboard-only and screen reader users.
**Action:** Always verify that interactive custom components have `role="button"`, `tabindex="0"`, an `onkeydown` handler for Enter/Space, `aria-label`, and a clear `:focus-visible` CSS state. Where possible, use native `<button>` tags instead to get this functionality out-of-the-box.

## 2024-05-20 - Label Association with Inputs Missing in Forms
**Learning:** Found multiple `<label>` tags in `src/dashboard/templates/index.html` missing `for` attributes connecting them to their respective `<select>` and `<input>` elements. Without this, users cannot click the label to focus the input, and screen readers lack proper context when reading the input fields. Additionally, the labels lacked a `cursor: pointer` style, meaning sighted users had no visual cue that clicking the label would work.
**Action:** Always ensure that every `<label>` is explicitly associated with its form control using the `for` attribute (matching the target element's `id`). When building custom forms, add `cursor: pointer` to labels to improve interaction affordance.

## 2024-05-22 - Data Filtering Needs Empty States
**Learning:** Found data tables (like the signals candidate pool) that simply rendered as blank when no results matched the current filter. This looks like a bug and leaves the user confused about whether the system is broken or the filters are just too strict.
**Action:** Whenever implementing client-side filtering that results in 0 items, explicitly render a clear, helpful empty state message instead of a blank table to guide the user to adjust their filters.

## 2024-05-23 - Async Form Dependency Loading Lacks Visual Feedback
**Learning:** Found that long-running network requests populating dropdown forms (like Slicer Fields) or fetching heavy data tables (like Signals Push) did not disable their associated submission buttons. This allowed users to prematurely click "Extract" or rapidly click "Refresh", resulting in errors or duplicate network requests.
**Action:** When a submission button relies on dynamically loaded data or is fetching heavy data itself, always set `btn.disabled = true` and provide a helpful `title` tooltip (e.g., "正在加载数据...") during the network request. Ensure `finally` block logic resets both the disabled state and the tooltip to prevent the UI from becoming permanently locked if the request fails.

## 2024-05-24 - Async Status Updates Lack Screen Reader Feedback
**Learning:** Found dynamic status text containers (like Slicer Status or Signal extraction logs) being injected into the DOM via JavaScript after async actions complete, but lacking `aria-live` attributes. This meant screen readers remained silent upon task completion, requiring blind users to manually hunt for the result message.
**Action:** Always wrap dynamic status message containers with `aria-live="polite"` and `aria-atomic="true"` so that async feedback (e.g., "✅ Extraction complete") is automatically announced to assistive technologies without interrupting the user.

## 2025-03-29 - [Dashboard Data/Chart Tabs]
**Learning:** Found a partial UI state where a single "Data" button would reveal a data table without providing a way to return to the Chart view. Implementing a proper `role="tablist"` with `role="tab"` and `aria-selected` attributes for mutually exclusive segments is crucial for screen readers to understand the view state.
**Action:** Always implement complete visual segmented controls (e.g. "Chart" and "Data") rather than standalone toggle buttons, and include full tablist ARIA semantics to ensure clear state changes.
