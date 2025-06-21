import * as child_process from "node:child_process";
import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter(),
		router: { type: "hash" },
		version: {
			name: `${child_process.execSync("git describe --tags").toString().trim()}|${child_process.execSync("git rev-parse --short HEAD").toString().trim()}`,
		},
	},
};

export default config;
