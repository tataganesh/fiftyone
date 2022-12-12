import { usePanel, usePanelTitle, useSpaces } from "../hooks";
import { PanelTabProps } from "../types";
import { panelNotFoundError } from "../utils";
import PanelIcon from "./PanelIcon";
import { StyleCloseButton, StyledTab } from "./StyledElements";

export default function PanelTab({ node, active, spaceId }: PanelTabProps) {
  const { spaces } = useSpaces(spaceId);
  const panelName = node.type;
  const panel = usePanel(panelName);
  const [title] = usePanelTitle(node.id);

  if (!panel) return panelNotFoundError(panelName);

  return (
    <StyledTab
      onClick={() => {
        if (!active) spaces.setNodeActive(node);
      }}
      active={active}
    >
      <PanelIcon name={panelName as string} />
      {title || panel.label}
      {!node.pinned && (
        <StyleCloseButton
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            spaces.removeNode(node);
          }}
        >
          x
        </StyleCloseButton>
      )}
    </StyledTab>
  );
}