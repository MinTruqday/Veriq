import DragHandle from "@tiptap/extension-drag-handle";
import Emoji, { emojis } from "@tiptap/extension-emoji";
import FileHandler from "@tiptap/extension-file-handler";
import Focus from "@tiptap/extension-focus";
import InvisibleCharacters from "@tiptap/extension-invisible-characters";
import ListKeymap from "@tiptap/extension-list-keymap";
import Mention from "@tiptap/extension-mention";
import UniqueID from "@tiptap/extension-unique-id";
import CharacterCount from "@tiptap/extension-character-count";
import CodeBlockLowlight from "@tiptap/extension-code-block-lowlight";
import Color from "@tiptap/extension-color";
import Details from "@tiptap/extension-details";
import DetailsContent from "@tiptap/extension-details-content";
import DetailsSummary from "@tiptap/extension-details-summary";
import FontFamily from "@tiptap/extension-font-family";
import Highlight from "@tiptap/extension-highlight";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Mathematics from "@tiptap/extension-mathematics";
import Placeholder from "@tiptap/extension-placeholder";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableOfContents from "@tiptap/extension-table-of-contents";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import TaskItem from "@tiptap/extension-task-item";
import TaskList from "@tiptap/extension-task-list";
import TextAlign from "@tiptap/extension-text-align";
import TextStyle from "@tiptap/extension-text-style";
import Typography from "@tiptap/extension-typography";
import Underline from "@tiptap/extension-underline";
import Youtube from "@tiptap/extension-youtube";
import StarterKit from "@tiptap/starter-kit";
import { common, createLowlight } from "lowlight";

const lowlight = createLowlight(common);

function insertImageFiles(editor, files, position) {
  const images = files.filter((file) => file.type.startsWith("image/"));
  if (position != null) editor.commands.setTextSelection(position);
  for (const file of images) {
    editor
      .chain()
      .focus()
      .setImage({ src: URL.createObjectURL(file), alt: file.name })
      .run();
  }
}

export function createQaExtensions(editable, placeholder, onTableOfContentsUpdate, onImageFiles) {
  return [
    StarterKit.configure({ codeBlock: false }),
    CodeBlockLowlight.configure({ lowlight }),
    Focus.configure({ className: "has-focus", mode: "all" }),
    ListKeymap.configure({
      listTypes: [
        { itemName: "listItem", wrapperNames: ["bulletList", "orderedList"] },
        { itemName: "taskItem", wrapperNames: ["taskList"] },
      ],
    }),
    UniqueID.configure({
      attributeName: "data-node-id",
      types: [
        "paragraph",
        "heading",
        "blockquote",
        "codeBlock",
        "listItem",
        "taskItem",
        "table",
        "tableRow",
        "tableHeader",
        "tableCell",
        "image",
        "youtube",
        "details",
      ],
      updateDocument: editable,
    }),
    Underline,
    Highlight.configure({ multicolor: true }),
    Subscript,
    Superscript,
    TextStyle,
    Color,
    FontFamily,
    TextAlign.configure({ types: ["heading", "paragraph"] }),
    Link.configure({
      autolink: true,
      linkOnPaste: true,
      openOnClick: !editable,
      HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" },
    }),
    Placeholder.configure({ placeholder }),
    CharacterCount,
    Typography,
    Emoji.configure({ emojis, enableEmoticons: true }),
    Mention.configure({
      HTMLAttributes: { class: "tiptap-mention" },
      suggestion: { char: "@", items: () => [] },
    }),
    InvisibleCharacters.configure({ visible: false, injectCSS: true }),
    FileHandler.configure({
      allowedMimeTypes: ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"],
      onPaste: (editor, files) => {
        if (!onImageFiles) return insertImageFiles(editor, files);
        void onImageFiles(files).then((nodes) => {
          if (!editor.isDestroyed && nodes.length)
            editor.chain().focus().insertContent(nodes).run();
        });
      },
      onDrop: (editor, files, position) => {
        if (!onImageFiles) return insertImageFiles(editor, files, position);
        void onImageFiles(files).then((nodes) => {
          if (!editor.isDestroyed && nodes.length)
            editor.chain().focus().setTextSelection(position).insertContent(nodes).run();
        });
      },
    }),
    Mathematics,
    Image.extend({
      addAttributes() {
        return { ...this.parent?.(), asset_id: { default: null }, width_cm: { default: 14 } };
      },
    }).configure({ allowBase64: false, HTMLAttributes: { loading: "lazy" } }),
    Youtube.configure({
      controls: true,
      nocookie: true,
      allowFullscreen: true,
      width: 640,
      height: 360,
    }),
    TaskList,
    TaskItem.configure({ nested: true }),
    Details.configure({ persist: true }),
    DetailsSummary,
    DetailsContent,
    Table.configure({ resizable: editable }),
    TableOfContents.configure({ onUpdate: onTableOfContentsUpdate }),
    TableRow,
    TableHeader,
    TableCell,
    ...(editable
      ? [
          DragHandle.configure({
            render: () => {
              const element = document.createElement("button");
              element.type = "button";
              element.className = "tiptap-drag-handle";
              element.setAttribute("aria-label", "Kéo khối nội dung");
              element.textContent = "⋮⋮";
              return element;
            },
          }),
        ]
      : []),
  ];
}
