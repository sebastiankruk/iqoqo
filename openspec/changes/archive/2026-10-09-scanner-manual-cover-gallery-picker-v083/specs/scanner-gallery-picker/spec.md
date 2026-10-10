## Purpose

Provides a mobile-friendly cover picker in manual scanner entry, enabling users to choose edited photos from their device gallery with live thumbnail preview.

## ADDED Requirements

### Requirement: Photo Gallery Cover Selection in Manual Entry
The manual entry interface SHALL allow users on mobile and desktop devices to select existing images from their photo library as the item cover without forcing camera capture.

#### Scenario: Selecting an image from mobile photo library

- **WHEN** a user opens the manual entry form on a mobile device
- **AND** taps "Choose from Photos"
- **THEN** the device opens the system photo picker/gallery
- **AND** the selected image is staged for cover upload.

#### Scenario: Displaying thumbnail preview of staged cover

- **WHEN** a user selects an image file or has a captured cover staged
- **THEN** the form renders a visual image thumbnail of the selected cover
- **AND** provides controls to remove or change the image.

#### Scenario: Removing staged cover

- **WHEN** a user clicks "Remove" on a staged cover image
- **THEN** the staged cover is cleared
- **AND** the form returns to the unselected cover picker state.
