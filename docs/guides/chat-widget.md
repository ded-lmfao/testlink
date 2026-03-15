# Chat Widget

## Documentation Index

Fetch the complete documentation index at:

<https://context7.com/docs/llms.txt>

Use this file to discover all available pages before exploring further.

Embed an AI-powered chat assistant on your documentation site.

The widget is a lightweight JavaScript snippet that renders a floating chat button. When clicked, it opens a chat panel where users can ask questions about your library and receive AI-generated answers grounded in your documentation.

!!! note
    The chat widget is available to library owners who have claimed their library.

## How It Works

1. A visitor clicks the chat bubble on your site.
2. They type a question about your library.
3. The widget searches your library's documentation on Context7.
4. An AI model generates an answer using the relevant documentation.
5. The response streams back in real time with markdown formatting.

## Setup

### 1) Claim your library

You must be a verified owner of the library on Context7.

### 2) Enable the widget

Open your library admin page:

```text
https://context7.com/{owner}/{repo}/admin
```

Go to the **Chat** tab and turn **Widget enabled** on.

### 3) Add allowed domains

Add the domains where the widget will be embedded. The widget works only on explicitly allowed domains.

Examples:

- `docs.example.com` — exact domain match
- `*.example.com` — all subdomains (e.g., `docs.example.com`, `blog.example.com`)
- `example.com` — root domain only

!!! warning
    The widget will not work on any external site until at least one allowed domain is added.

### 4) Save settings

Click **Save** in the admin panel.

### 5) Add the script tag

Add this script tag to your root layout/HTML file so it loads on every page:

```html
<script src="https://context7.com/widget.js" data-library="/websites/revvlink_revvlabs_in_api"></script>
```

This project already embeds the widget globally via the MkDocs Material override.

## Framework Detection (this project)

This docs site uses **MkDocs + Material for MkDocs**.

Widget placement:

- Root override file: `docs/overrides/main.html`
- Built output includes script on all pages (e.g. home and API pages)

## Customization

Optional widget attributes:

| Attribute          | Description                           | Default                    |
|-------------------|---------------------------------------|----------------------------|
| `data-library`     | Library identifier (required)         | —                          |
| `data-color`       | Brand color (hex)                     | `#059669`                  |
| `data-position`    | Widget position                       | `bottom-right`             |
| `data-placeholder` | Input placeholder text                | `Ask about the docs...`    |

### Example: custom color + position

```html
<script
  src="https://context7.com/widget.js"
  data-library="/websites/revvlink_revvlabs_in_api"
  data-color="#0070F3"
  data-position="bottom-left"
></script>
```

### Example: custom placeholder

```html
<script
  src="https://context7.com/widget.js"
  data-library="/websites/revvlink_revvlabs_in_api"
  data-placeholder="Ask me anything about RevvLink..."
></script>
```

### Position options

| Value          | Description                      |
|----------------|----------------------------------|
| `bottom-right` | Fixed to the bottom-right corner |
| `bottom-left`  | Fixed to the bottom-left corner  |

## Domain Configuration

You can configure up to **20 allowed domains** per library. Domain validation is enforced server-side; non-allowed origins are rejected with HTTP 403.

### Patterns

| Pattern            | Matches                                                                         |
|--------------------|---------------------------------------------------------------------------------|
| `docs.example.com` | Only `docs.example.com`                                                         |
| `*.example.com`    | Any subdomain including `example.com` itself                                    |
| `example.com`      | Only root domain `example.com`                                                  |

### Manage domains

1. Open the **Chat** tab in your Context7 library admin.
2. Click **Add domain** and enter a domain pattern.
3. Click **Save**.
4. To remove a domain, use the delete icon and save.
