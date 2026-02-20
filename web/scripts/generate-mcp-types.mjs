#!/usr/bin/env node
/**
 * Generate TypeScript types from MCP tool schemas.
 */

import { compileFromFile } from 'json-schema-to-typescript';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const schemasPath = path.join(__dirname, '../../schemas/mcp-tools.json');
const outputPath = path.join(__dirname, '../src/types/mcp-generated.ts');

async function generateTypes() {
  try {
    // Read the MCP tools schema
    const schemasContent = await fs.readFile(schemasPath, 'utf8');
    const schemas = JSON.parse(schemasContent);

    console.log(`\n🔧 Generating TypeScript types from MCP schemas...`);
    console.log(`   Schema version: ${schemas.version}`);
    console.log(`   Tools found: ${Object.keys(schemas.tools).length}\n`);

    let output = `/**
 * Auto-generated TypeScript types from MCP server tool schemas.
 * DO NOT EDIT MANUALLY - regenerate using \`npm run generate-types\`
 *
 * Schema version: ${schemas.version}
 * Generated: ${new Date().toISOString()}
 */

/**
 * MCP Schema Version - used to verify client/server compatibility
 */
export const MCP_SCHEMA_VERSION = "${schemas.version}";

`;

    // Generate types for each tool
    for (const [toolName, toolDef] of Object.entries(schemas.tools)) {
      const capitalizedName = toolName
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('');

      // Generate input type
      if (toolDef.input && Object.keys(toolDef.input).length > 0) {
        output += `/**
 * Input parameters for ${toolName}
 * ${toolDef.description.split('\n')[0]}
 */
export interface ${capitalizedName}Input {\n`;

        if (toolDef.input.properties) {
          for (const [propName, propDef] of Object.entries(toolDef.input.properties)) {
            const isRequired = toolDef.input.required?.includes(propName);
            const optional = isRequired ? '' : '?';
            const tsType = jsonSchemaTypeToTs(propDef);
            output += `  ${propName}${optional}: ${tsType};\n`;
          }
        }
        output += `}\n\n`;
      }

      // Generate output type
      if (toolDef.output) {
        output += `/**
 * Response from ${toolName}
 * ${toolDef.description.split('\n')[0]}
 */
export type ${capitalizedName}Response = ${jsonSchemaTypeToTs(toolDef.output)};\n\n`;
      }
    }

    // Add a union type of all tool names
    output += `/**
 * All available MCP tool names
 */
export type MCPToolName = ${Object.keys(schemas.tools).map(name => `"${name}"`).join(' | ')};\n\n`;

    // Add a helper type for tool results
    output += `/**
 * Helper type to get the response type for a specific tool
 */
export type MCPToolResponse<T extends MCPToolName> = \n`;
    for (const toolName of Object.keys(schemas.tools)) {
      const capitalizedName = toolName
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('');
      output += `  T extends "${toolName}" ? ${capitalizedName}Response :\n`;
    }
    output += `  never;\n`;

    // Write the output
    await fs.writeFile(outputPath, output, 'utf8');

    console.log(`✅ Generated TypeScript types successfully!`);
    console.log(`   Output: ${outputPath}\n`);
  } catch (error) {
    console.error('❌ Error generating types:', error);
    process.exit(1);
  }
}

/**
 * Convert JSON Schema type to TypeScript type
 */
function jsonSchemaTypeToTs(schema) {
  if (!schema) return 'unknown';

  // Handle type array (union types like string | null)
  if (Array.isArray(schema.type)) {
    return schema.type.map(t => primitiveTypeToTs(t)).join(' | ');
  }

  // Handle single type
  if (schema.type === 'object') {
    if (!schema.properties || Object.keys(schema.properties).length === 0) {
      return 'Record<string, unknown>';
    }

    let obj = '{\n';
    for (const [propName, propDef] of Object.entries(schema.properties)) {
      const isRequired = schema.required?.includes(propName);
      const optional = isRequired ? '' : '?';
      obj += `    ${propName}${optional}: ${jsonSchemaTypeToTs(propDef)};\n`;
    }
    obj += '  }';
    return obj;
  }

  if (schema.type === 'array') {
    const itemType = schema.items ? jsonSchemaTypeToTs(schema.items) : 'unknown';
    return `Array<${itemType}>`;
  }

  return primitiveTypeToTs(schema.type);
}

/**
 * Convert JSON Schema primitive type to TypeScript
 */
function primitiveTypeToTs(type) {
  switch (type) {
    case 'string':
      return 'string';
    case 'integer':
    case 'number':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'null':
      return 'null';
    default:
      return 'unknown';
  }
}

generateTypes();
