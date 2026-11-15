# LocalGuard

> Lightweight, offline security and metadata checks for your own local files.

<p align="center">
  <img src="assets/localguard-hero.svg" alt="Animated LOCALGUARD banner featuring Python, HTML5, and CSS3" width="100%">
</p>

## Overview

LocalGuard is a dependency-free Python command-line tool for helping developers
review a local project before sharing it. It checks text files for likely
accidentally committed credentials and inspects supported documents for
embedded metadata that may reveal author names or document details.

### Features

- Detects common credential patterns in UTF-8 text files.
- Keeps matched credential values out of the scan output.
- Inspects Office Open XML core properties and basic PDF info fields.
- Reports when JPEG EXIF or PNG text metadata is present.
- Provides readable terminal output and machine-readable JSON.
- Works offline; it does not enumerate hosts, harvest information about people,
  attempt logins, or exploit systems.

> **Scope:** Use LocalGuard to audit files you own or are authorized to review.
> Its pattern checks can produce false positives and are not a replacement for
> secret management or a dedicated security review.

## Programming Languages

- Python
- HTML5
- CSS3

<p align="center">
  <img src="assets/localguard-languages-animated.svg" alt="Animated Python, HTML5, and CSS3 cards" width="620">
</p>

## Logo

<p align="center">
  <img src="assets/localguard-logo-animated.svg" alt="Animated LOCALGUARD shield and checkmark logo" width="600">
</p>

Open [localguard-logo-preview.html](localguard-logo-preview.html) in a browser
to preview the animated logo. The [animated hero SVG](assets/localguard-hero.svg),
[static hero PNG](assets/localguard-hero.png), [static logo SVG](assets/localguard-logo.svg),
[animated logo SVG](assets/localguard-logo-animated.svg),
[transparent logo PNG](assets/localguard-logo.png), and
[favicon](assets/localguard-favicon.svg) are available for use in a website,
README, or app. The SVG animations respect reduced-motion preferences.

## Requirements

- Python 3.10 or newer

## Install

From the project directory:

```powershell
py -m pip install -e .
```

## Usage

Scan the current project for likely credentials:

```powershell
localguard scan
```

Scan a specific directory or emit JSON:

```powershell
localguard scan .\path\to\project
localguard scan .\path\to\project --json
```

Inspect supported embedded metadata in your local files:

```powershell
localguard metadata .\path\to\project
localguard metadata .\path\to\project --json
```

The credential scanner checks UTF-8 text files up to 1 MB. Both commands skip
common generated and dependency directories and ignore symlinks. The metadata
command displays metadata it finds; review its output before sharing files.

Credential scan exit codes are `0` for no findings, `1` when findings are
present, and `2` when scanning encounters errors or the supplied path is not a
directory.

## Development

Run the test suite with:

```powershell
py -m unittest discover -s tests
```

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
