import { formatName } from "./format";
import React from "react";

const legacy = require("./legacy");
export { Widget } from "./widget";

const lazyModule = import("./lazy.js");
const harmlessText = "require('./fake')";
const harmlessTemplate = `import "./fake"`;
const harmlessPattern = /require\("\.\/fake"\)/;
// import "./fake";

export { formatName, legacy, lazyModule, React, harmlessPattern, harmlessTemplate, harmlessText };
