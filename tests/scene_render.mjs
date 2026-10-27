import fs from "node:fs";
const source = fs.readFileSync("custom_components/ha_dial/www/scene.js", "utf8");
const { rasterize } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const scenes = JSON.parse(fs.readFileSync(0, "utf8"));
for (const scene of scenes) process.stdout.write(Buffer.from(rasterize(scene, scene.test_local_value ?? -1)));
