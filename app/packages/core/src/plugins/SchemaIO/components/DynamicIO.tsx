import { PluginComponentType, useActivePlugins } from "@fiftyone/plugins";
import { isNullish } from "@fiftyone/utilities";
import { get, isEqual, set } from "lodash";
import React, { useEffect, useMemo } from "react";
import { isPathUserChanged } from "../hooks";
import { getComponent, getErrorsForView, isCompositeView } from "../utils";
import { AncestorsType, SchemaType, ViewPropsType } from "../utils/types";
import ContainerizedComponent from "./ContainerizedComponent";

export default function DynamicIO(props: ViewPropsType) {
  const { data, schema, onChange, path } = props;
  const customComponents = useCustomComponents();
  const Component = getComponent(schema, customComponents);
  const computedSchema = getComputedSchema(props);
  const { default: defaultValue } = computedSchema;

  // todo: need to improve initializing default value in state
  useEffect(() => {
    if (
      !isCompositeView(schema) &&
      !isEqual(data, defaultValue) &&
      !isPathUserChanged(path) &&
      !isNullish(defaultValue)
    ) {
      onChange(path, defaultValue, computedSchema);
    }
  }, [defaultValue]);

  const onChangeWithSchema = useMemo(() => {
    return (
      path: string,
      value: unknown,
      schema?: SchemaType,
      ancestors: AncestorsType = {}
    ) => {
      const isComposite = isCompositeView(computedSchema);
      const subSchema = !isComposite ? computedSchema : undefined;
      const currentPath = props.path;
      const computedAncestors = { ...ancestors };
      if (isComposite) {
        computedAncestors[currentPath] = computedSchema;
      }
      onChange(path, value, schema ?? subSchema, computedAncestors);
    };
  }, [onChange, computedSchema, props.path]);

  return (
    <ContainerizedComponent {...props} schema={computedSchema}>
      <Component
        {...props}
        onChange={onChangeWithSchema}
        schema={computedSchema}
        validationErrors={getErrorsForView(props)}
      />
    </ContainerizedComponent>
  );
}

function useCustomComponents() {
  const pluginComponents =
    useActivePlugins(PluginComponentType.Component, {}) || [];

  return pluginComponents.reduce((componentsByName, component) => {
    componentsByName[component.name] = component.component;
    return componentsByName;
  }, {});
}

function schemaWithInheritedDefault(
  schema: ViewPropsType["schema"],
  parentSchema: ViewPropsType["parentSchema"],
  path: ViewPropsType["relativePath"]
) {
  const providedDefault = get(schema, "default");
  const inheritedDefault = get(parentSchema, `default.${path}`);
  const computedDefault = providedDefault ?? inheritedDefault;
  return { ...schema, default: computedDefault };
}

function schemaWithInheritedVariant(
  schema: ViewPropsType["schema"],
  parentSchema: ViewPropsType["parentSchema"]
) {
  if (isNullish(get(schema, "view.variant"))) {
    set(schema, "view.variant", get(parentSchema, "view.variant"));
    set(schema, "view.compact", true);
  }
  if (isNullish(get(schema, "view.color"))) {
    set(schema, "view.color", get(parentSchema, "view.color"));
  }
  return schema;
}

function getComputedSchema(props: ViewPropsType) {
  const { schema, parentSchema, relativePath } = props;
  let computedSchema = schemaWithInheritedDefault(
    schema,
    parentSchema,
    relativePath
  );
  const parentView = parentSchema?.view?.name;
  if (parentView === "MenuView") {
    computedSchema = schemaWithInheritedVariant(computedSchema, parentSchema);
  }
  return computedSchema;
}
