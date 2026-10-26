export function copyValue(value) {
  return value === undefined ? undefined : structuredClone(value);
}

export function chooseFields(result, incoming, fieldKeys) {
  const next = { ...result };
  for (const key of fieldKeys) {
    if (Object.hasOwn(incoming || {}, key)) next[key] = copyValue(incoming[key]);
    else delete next[key];
  }
  return next;
}

export function chooseStep(result, incoming) {
  const steps = [...(result.steps || [])];
  const index = steps.findIndex((step) => step.id === incoming.id);
  if (index < 0) steps.push(copyValue(incoming));
  else steps[index] = copyValue(incoming);
  return { ...result, steps: steps.map((step, order) => ({ ...step, order: order + 1 })) };
}

export function chooseStepSource(result, id, incoming) {
  if (!incoming) return removeStep(result, id);
  return chooseStep(result, incoming);
}

export function moveStep(result, id, offset) {
  const steps = [...(result.steps || [])];
  const index = steps.findIndex((step) => step.id === id);
  const target = index + offset;
  if (index < 0 || target < 0 || target >= steps.length) return result;
  [steps[index], steps[target]] = [steps[target], steps[index]];
  return { ...result, steps: steps.map((step, order) => ({ ...step, order: order + 1 })) };
}

export function removeStep(result, id) {
  return {
    ...result,
    steps: (result.steps || [])
      .filter((step) => step.id !== id)
      .map((step, order) => ({ ...step, order: order + 1 })),
  };
}

export function comparedStepIds(original, proposal, result) {
  return [
    ...new Set(
      [...(result?.steps || []), ...(proposal?.steps || []), ...(original?.steps || [])].map(
        (step) => step.id,
      ),
    ),
  ];
}

export function fieldDifference(original, proposal) {
  if (JSON.stringify(original) === JSON.stringify(proposal)) return "Không thay đổi";
  if (original === undefined || original === null) return "AI bổ sung";
  if (proposal === undefined || proposal === null) return "AI lược bỏ";
  return "AI thay đổi";
}
