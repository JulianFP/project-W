import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
	input: "http://localhost:5000/openapi.json",
	output: "src/lib/generated",
	plugins: [
		{
			name: "@hey-api/typescript",
			enums: "javascript",
		},
		{
			name: "@hey-api/transformers",
			dates: true,
		},
		{
			name: "@hey-api/client-fetch",
			runtimeConfigPath: "$lib/utils/hey-api",
		},
		{
			name: "@hey-api/sdk",
			transformer: true,
		},
	],
});
