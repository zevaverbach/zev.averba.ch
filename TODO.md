# TODO

- [ ] get endpoints working
  - [ ] disallow "post" calls to the static pages (nginx)

- [ ] disallow identical titles (in DB preferably)

## Design

- [ ] revamp the CSS grid stuff, the layout is a mess:
  - [ ] use a single column on mobile/< 1000 px display
- [ ] center toc items on mobile
- [ ] underline "posts" and "about" in nav on mobile!
- [ ] change "toc" to "posts"
- [ ] more space between nav and title everywhere, but probably more on mobile
- [ ] make two columns of items in toc on large screens
- [ ] make the background in light mode lighter
- [ ] change the link colors in dark mode, green is gross (maybe just stay with yellow even with hover...)
- [ ] make a dark/light mode button
- [ ] add syntax highlighting
  - PrismJS
- [x] remove "Posts" title entirely
- [x] make 'logo' larger on small screen
- [x] make H1 title a little larger when small screen

## Content
- [ ] make a "contact" page
- [ ] make a page at "/"
- [ ] bring content over from old site
- [ ] add content from Twilio etc.
- [ ] make a timeline
- [ ] blog about the things you've built, and maybe make pages for them

### SEO
- [ ] generate sitemap on every change and submit it to Google
  - [ ] https://stackoverflow.com/a/13906868/4386191
    - there's no limit to how often you re-submit it
  - [ ] first create internal links automatically
    - [https://moz.com/learn/seo/internal-link]
    - [ ] limit it to 150 links in a given page
- [ ] web standard validator programmatically?
- [ ] detect similar or duplicate pages and disallow it, it fucks up SEO
- [ ] set other metas
  - html lang?
  - [optimize for crawlers](https://www.wordstream.com/blog/ws/2020/11/17/website-visibility)
