# Open STEP Viewer

This project includes a local web app that reads STEP files from `models/step`, parses them in the browser with `occt-import-js`, and renders them with `three.js`.

## Run

1. Install dependencies with `npm install`
2. Start the app with `npm run start`
3. Open `http://127.0.0.1:3000`

## Notes

- No Autodesk Platform Services account is required.
- The browser loads and triangulates STEP files locally, so large files can take noticeable time.
- The app currently supports `.step` and `.stp` files from `models/step`.
