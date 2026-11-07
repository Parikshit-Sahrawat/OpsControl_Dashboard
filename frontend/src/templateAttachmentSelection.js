// Resource edits preserve the selected immutable version. Upgrades are explicit.
export function attachmentVersion(template, existing) {
  const version = existing ? existing.template_version : template.version;
  if (!Number.isInteger(version) || version < 1) throw new Error("Template version must be a positive integer");
  return version;
}
