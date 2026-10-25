// The preset file is a copy of ui/presets.json; Vite imports JSON, and this tells TypeScript its shape.
declare module "*/presets.json" {
  const value: { presets: unknown[] };
  export default value;
}
