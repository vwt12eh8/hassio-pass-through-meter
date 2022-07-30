![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)
[![Validate with hassfest](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/hassfest.yml/badge.svg)](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/hassfest.yml)
[![HACS Action](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/hacs.yml/badge.svg)](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/hacs.yml)
[![CodeQL](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/vwt12eh8/hassio-pass-through-meter/actions/workflows/codeql-analysis.yml)

# Pass-Through Meter
Used for devices with two energy sensors, one on the input side and one on the output side.

This integration isolates the energy consumed on the fly without being charged to the battery to another sensor when the device is used while charging.

To use this integration, the device must provide two entities, "Total Input Power" and "Total Output Power".

During the pass-through, these entities should be such that, for example, if 1Wh of power is added to the input side, the output side should also be immediately added by 1Wh.

When this integration is set up, the two entities specified are converted into three entities: power charged to the battery, power consumed from the battery, and power consumed on the spot without going through the battery.

## Precautions
Since this entity only observes the change in value and calculates the power that is thought to be passing, there is no guarantee that the power calculated as passing is absolutely not passing through the battery.

Also, restarting HomeAssistant or reloading the integration may cause errors to accumulate depending on timing.

If the two source entities are updated at different times, the Charged and Discharged entities may decrease in value once increased, but this is a necessary action to correct what was temporarily calculated as not a pass-through.

## Installation
This integration is not included by default and must be installed by yourself to use it.

Two methods are available, and you can choose one or the other.
- Install as a custom repository via HACS
- Manually download and extract to the custom_components directory

Once installed, after restarting Home Assistant, you can start integration as usual from Add Integration.
