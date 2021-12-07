# Flow

## Input
- change 'content' via API calls
- change 'content' via DB queries

### Next
- require authorization to make those changes
- allow editing of the site if you're authenticated and authorized

## On Change
- render/re-render the relevant page
- put the rendered page on the site
- regenerate and deploy the TOC
- regenerate and re-submit the sitemap.xml

### Next
- deploy to Cloudflare/S3/Render


- [ ] render the pages whenever
  - [ ] maybe re-make the site based on Svelte-Kit or Next.js
    - maybe both? get some muscle memory
  - [ ] add auth so that only privileged people can see my real-time updates
  - [ ] link to TOC in main page
  - [ ] recent posts on main page

- [ ] bring content over from old site
- [ ] add content from Twilio etc.
- [ ] support code blocks (PrismJS)
- [ ] make a timeline
- [ ] blog about the things you've built, and maybe make pages for them
- [ ] generate sitemap on every change and submit it to Google
  - [ ] https://stackoverflow.com/a/13906868/4386191
    - there's no limit to how often you re-submit it
  - [ ] first create internal links automatically
    - [https://moz.com/learn/seo/internal-link]
    - [ ] limit it to 150 links in a given page
- [ ] web standard validator programmatically?
- [ ] detect similar or duplicate pages and disallow it, it fucks up SEO
- [ ] dark/light mode
- [ ] set other metas
  - html lang?
  - [optimize for crawlers](https://www.wordstream.com/blog/ws/2020/11/17/website-visibility)
