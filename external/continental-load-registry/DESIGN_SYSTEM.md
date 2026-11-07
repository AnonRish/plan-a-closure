# Observatory Design System

The registry uses a research-observatory presentation system rather than a generic dashboard template.

## Benchmark research

The design was informed by current public examples and documentation from:

- Linear: calm information-dense navigation, consistent tabs and headers, reduced visual noise, contextual filters and glanceable dashboards.
- Apple Human Interface Guidelines: purpose, agency, simplicity, hierarchy, craft, delight, progressive disclosure, and explicit interface states.
- Vercel Web Interface Guidelines: deliberate alignment, responsive behavior, visible focus, tabular numbers, concise copy, explicit empty/error/sparse states, and restrained animation.
- Stripe: responsive presentation and attention to small interaction details.
- Awwwards/CSS Awards galleries: visual direction, interaction, usability, and technical execution as a complete experience.

## Applied rules

### Navigation
The global observatory navigation is a sticky, horizontally scrollable tab bar: Overview · Map · Queues · Connection Targets · Evidence · Track 3 · Research Ops · Methodology.

### Density
Dense data is not removed; it is staged. Primary information is shown at a glance. Detailed fields use pagination, filters, expandable rows, or dedicated pages.

### Hierarchy
Primary content receives stronger contrast and typography. Supporting chrome recedes. Status labels always include text, not color alone.

### Motion
Motion is limited to small state transitions and a page progress indicator. Reduced-motion preferences are respected.

### Responsive behavior
Navigation scrolls horizontally on narrow screens. Large tables remain intentionally scrollable. Detailed records collapse into expandable blocks rather than forcing every field onto mobile.

### Completeness
A complete interface accounts for every field and every state. NOT PUBLICLY RETAINED, UNKNOWN, NO_PUBLIC_RECORD, and similar states are explicit rather than rendered as unexplained blanks.

### Research UX
Research tasks are site-specific and actionable. Search links are discovery aids; canonical evidence still requires source review, scope verification, provenance capture and explicit ingestion.

## Do not regress

- Do not turn unknowns into positive facts.
- Do not add another always-visible table when progressive disclosure would work.
- Do not use color as the only status cue.
- Do not add animation without a user-facing purpose.
- Do not widen the page until the content becomes difficult to scan.
- Do not duplicate controls without a clear reason.

The goal is to make the registry feel unusually polished because the information architecture is disciplined, not because decorative effects cover structural clutter.