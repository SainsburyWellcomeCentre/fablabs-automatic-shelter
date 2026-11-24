# Automatic Shelter

A Harp-controlled shelter actuator system for positioning three house sections, three doors, two blocks, and an arm.

## Actuators Registers

| Actuator | Position | Status | Torque | Speed |
| -------- | -------- | ------ | ------ | ----- |
| House 1  | 0x20     | 0x30   | 0x40   | 0x50  |
| House 2  | 0x21     | 0x31   | 0x41   | 0x51  |
| House 3  | 0x22     | 0x32   | 0x42   | 0x52  |
| Door 1   | 0x23     | 0x33   | 0x43   | 0x53  |
| Door 2   | 0x24     | 0x34   | 0x44   | 0x54  |
| Door 3   | 0x25     | 0x35   | 0x45   | 0x55  |
| Block 1  | 0x26     | 0x36   | 0x46   | 0x56  |
| Block 2  | 0x27     | 0x37   | 0x47   | 0x57  |
| Arm      | 0x28     | 0x38   | 0x48   | 0x58  |

For details on the register schema, see `device.yml`.

## Firmware Development

For information on setting up the development environment and flashing firmware onto the development board, please refer to [`Firmware Development`](firmware/README.md).

## Bonsai Example

Open `software/bonsai/shelter.bonsai` in Bonsai. The workflow provides keyboard controls for the actuators and communicates with the device using Harp messages.

Review the selected COM port and target device settings before opening the workflow. Start in a low-torque configuration and test one actuator at a time.

## License

See [`LICENSE`](LICENSE) for the licenses applying to this project.

## Contributing

1. Fork the repository.
2. Create a focused branch for your change.
3. Update the corresponding firmware constants and `device.yml` schema when register behavior changes.
4. Test on the target hardware before opening a pull request.

## Contact

- **Author:** Sainsbury Wellcome Centre FabLabs
- **Email:** [swc.fablabs@ucl.ac.uk](mailto:swc.fablabs@ucl.ac.uk)
- **Website:** [FabLabs Documentation](https://www.sainsburywellcomecentre.org/content/fablab)
