# Circular Drive Initiative (CDI) Brand Colors

Canonical definitions for digital and print. The CSS variable file `src/cdi_health/assets/cdi_brand_palette.css` mirrors these values for the CDI Health HTML report and other UI.

## Primary palette

| Name | PMS | RGB | HEX | CMYK |
|------|-----|-----|-----|------|
| **Simply Green** | PMS 17-5936 | R=19, G=156, B=122 | `#139C7A` | C=82, M=13, Y=69, K=1 |
| **Foliage Green** | PMS 18-6018 | R=59, G=115, B=81 | `#3B7351` | C=79, M=34, Y=77, K=20 |
| **Green Spruce** | PMS 16-5820 | R=92, G=146, B=121 | `#5C9279` | C=67, M=26, Y=59, K=5 |
| **Lilac Gray** | PMS 16-3905 | R=146, G=153, B=166 | `#9298A6` | C=46, M=35, Y=27, K=0 |
| **Real Teal** | PMS 18-4018 | R=61, G=96, B=114 | `#3E6071` | C=80, M=54, Y=41, K=18 |

## Color usage guidelines

- **Maintain consistency:** Use the specified brand colors so materials stay visually coherent.
- **Accessibility:** Combine colors so text and interactive elements meet readability and inclusivity standards (contrast ratios).
- **Color variations:** Do not alter hues or tints without approval.
- **Contrast:** Keep sufficient contrast between text and background for readability.

## Semantic mapping (reports / UI)

The palette file maps these to UI tokens (`--bg`, `--text`, `--accent`, etc.) tuned for light backgrounds and readable body copy while keeping Simply Green as the primary accent.
