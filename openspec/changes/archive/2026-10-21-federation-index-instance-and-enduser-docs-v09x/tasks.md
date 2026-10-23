## 1. Connected Libraries Directory

- [x] 1.1 Implement public directory API endpoint (`/api/v1/federation/directory`) serving trusted peer instance statistics
- [x] 1.2 Create frontend directory page (`frontend/app/federation/directory/page.tsx`) rendering connected library cards and links

## 2. In-App Documentation Hub & Menu Cleanup

- [x] 2.1 Create documentation route (`frontend/app/help/page.tsx` and `frontend/app/help/[slug]/page.tsx`)
- [ ] 2.2 Replace initial documentation with the 5 comprehensive bilingual (`en` + `pl`) guides (`frbr-hierarchy`, `camera-to-catalog`, `privacy-sharing-social`, `federation-architecture`, `curators-handbook`) and 7 visual assets in `frontend/public/images/help/` (replacing Mermaid blocks and stripping image generation prompts)
- [ ] 2.3 Upgrade Markdown presentation in `RichText` / `/help/[slug]` to render GFM pipe tables, styled figure images, and category navigation
- [ ] 2.4 Rename `"Help & Feedback"` menu item to `"Requests"` (`"Zgłoszenia"`) and add the `"Curator Escalations"` tab (`MyEscalations`) inside `/feedback`
- [ ] 2.5 Update frontend unit and E2E tests for the 5 help guides and unified Requests view
