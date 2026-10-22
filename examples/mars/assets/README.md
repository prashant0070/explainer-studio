# Mars example — image assets (not bundled)

The example spec references four NASA stills. They are **public domain under NASA's
media guidelines**, but this repo bundles no third-party media, so download them
yourself into `examples/mars/assets/nasa/`:

| File | Item | Credit | Where |
|---|---|---|---|
| `PIA00407.jpg` | Global Color Views of Mars (Viking mosaic) | NASA/JPL/USGS | https://images.nasa.gov/details/PIA00407 |
| `PIA22521.jpg` | Shades of Martian Darkness (dust-opacity **simulation**) | NASA/JPL-Caltech/TAMU | https://images.nasa.gov/details/PIA22521 |
| `PIA22487.jpg` | Mars Before and After Dust Storm (MRO MARCI) | NASA/JPL-Caltech/MSSS | https://images.nasa.gov/details/PIA22487 |
| `PIA22929.jpg` | Opportunity's last image | NASA/JPL-Caltech | https://images.nasa.gov/details/PIA22929 |

Keep the on-screen credits from `project.yaml` if you reuse them. NASA does not
endorse this video; don't use NASA logos.

No images? Build the demo anyway with labelled placeholder art:

```bash
explainer build examples/mars/project.yaml --no-vo --placeholders
```
