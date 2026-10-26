"use client";
import { useEffect, useState } from "react";
import { BubbleMenu, EditorContent, FloatingMenu, useEditor } from "@tiptap/react";
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  AtSign,
  Bold,
  Braces,
  ChevronDownSquare,
  Code2,
  Columns3,
  Heading1,
  Heading2,
  Heading3,
  Highlighter,
  ImagePlus,
  Italic,
  Eye,
  Link as LinkIcon,
  List,
  ListChecks,
  ListOrdered,
  Minus,
  Quote,
  Redo2,
  Rows3,
  Sigma,
  Strikethrough,
  Subscript as SubscriptIcon,
  Superscript as SuperscriptIcon,
  Table2,
  Trash2,
  Underline as UnderlineIcon,
  Undo2,
  Unlink,
  Smile,
  Youtube as YoutubeIcon,
} from "lucide-react";
import { useActionDialog } from "../components/WorkspacePrimitives";
import { createQaExtensions } from "./extensions";

export default function DocumentEditor({
  value,
  onChange,
  label,
  minHeight = "min-h-40",
  readOnly = false,
  ignoreUnfocusedUpdates = false,
}) {
  const [tableOfContents, setTableOfContents] = useState([]);
  const { ask, dialog } = useActionDialog();
  const editor = useEditor({
    immediatelyRender: false,
    extensions: createQaExtensions(
      !readOnly,
      label ? `Nhập ${label.toLocaleLowerCase("vi")}` : "Nhập nội dung",
      setTableOfContents,
    ),
    content: value,
    editable: !readOnly,
    editorProps: {
      attributes: {
        class: `testing-tiptap ${readOnly ? "min-h-0" : minHeight}`,
        role: "textbox",
        "aria-label": label,
        spellcheck: "true",
      },
    },
    onUpdate({ editor: current }) {
      if (ignoreUnfocusedUpdates && !current.isFocused) return;
      onChange?.(current.getJSON());
    },
  });

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!readOnly, false);
    if (editor.isFocused) return;
    if (JSON.stringify(editor.getJSON()) !== JSON.stringify(value)) {
      editor.commands.setContent(value, false);
    }
  }, [editor, readOnly, value]);

  if (!editor) return <div className={`${readOnly ? "min-h-0" : minHeight} skeleton`} />;

  if (readOnly) {
    return (
      <div className="overflow-hidden rounded-panel border border-border bg-surface">
        <EditorContent editor={editor} />
      </div>
    );
  }

  const addLink = async () => {
    await ask({
      title: "Thêm hoặc sửa liên kết",
      description: "Nhập địa chỉ web hoặc email; để trống để bỏ liên kết hiện tại",
      fields: [
        {
          name: "href",
          label: "Địa chỉ liên kết",
          initialValue: editor.getAttributes("link").href || "https://",
        },
      ],
      confirmLabel: "Lưu liên kết",
      onConfirm: ({ href }) => {
        if (!href.trim()) {
          editor.chain().focus().extendMarkRange("link").unsetLink().run();
          return;
        }
        let parsed;
        try {
          parsed = new URL(href.trim());
        } catch {
          throw new Error("Nhập một địa chỉ HTTP, HTTPS hoặc email hợp lệ");
        }
        if (!["http:", "https:", "mailto:"].includes(parsed.protocol)) {
          throw new Error("Chỉ hỗ trợ liên kết HTTP, HTTPS hoặc email");
        }
        editor.chain().focus().extendMarkRange("link").setLink({ href: parsed.toString() }).run();
      },
    });
  };

  const addImage = async () => {
    await ask({
      title: "Chèn hình ảnh",
      fields: [
        { name: "src", label: "Địa chỉ hình ảnh", required: true },
        { name: "alt", label: "Mô tả hình ảnh", required: true },
      ],
      confirmLabel: "Chèn hình ảnh",
      onConfirm: ({ src, alt }) => {
        let parsed;
        try {
          parsed = new URL(src.trim());
        } catch {
          throw new Error("Nhập một địa chỉ hình ảnh HTTP hoặc HTTPS hợp lệ");
        }
        if (!["http:", "https:"].includes(parsed.protocol)) {
          throw new Error("Hình ảnh chỉ hỗ trợ địa chỉ HTTP hoặc HTTPS");
        }
        editor.chain().focus().setImage({ src: parsed.toString(), alt: alt.trim() }).run();
      },
    });
  };

  const addMath = async () => {
    await ask({
      title: "Chèn công thức",
      fields: [{ name: "latex", label: "Công thức LaTeX", required: true, multiline: true }],
      confirmLabel: "Chèn công thức",
      onConfirm: ({ latex }) => {
        editor.chain().focus().insertContent(`$${latex.trim()}$`).run();
      },
    });
  };

  const addEmoji = async () => {
    await ask({
      title: "Chèn emoji",
      fields: [{ name: "shortcode", label: "Mã emoji", initialValue: "smile", required: true }],
      confirmLabel: "Chèn emoji",
      onConfirm: ({ shortcode }) => {
        editor.chain().focus().setEmoji(shortcode.trim()).run();
      },
    });
  };

  const addMention = async () => {
    await ask({
      title: "Nhắc người dùng hoặc vai trò",
      fields: [{ name: "label", label: "Tên người dùng hoặc vai trò", required: true }],
      confirmLabel: "Chèn nhắc tên",
      onConfirm: ({ label: mentionLabel }) => {
        const label = mentionLabel.trim();
        editor
          .chain()
          .focus()
          .insertContent({ type: "mention", attrs: { id: label, label } })
          .insertContent(" ")
          .run();
      },
    });
  };

  const addYoutube = async () => {
    await ask({
      title: "Chèn video YouTube",
      fields: [{ name: "src", label: "Địa chỉ video YouTube", required: true }],
      confirmLabel: "Chèn video",
      onConfirm: ({ src }) => {
        let parsed;
        try {
          parsed = new URL(src.trim());
        } catch {
          throw new Error("Nhập một địa chỉ video YouTube hợp lệ");
        }
        if (!["http:", "https:"].includes(parsed.protocol)) {
          throw new Error("Địa chỉ video phải dùng HTTP hoặc HTTPS");
        }
        editor
          .chain()
          .focus()
          .setYoutubeVideo({ src: parsed.toString(), width: 640, height: 360 })
          .run();
      },
    });
  };

  const toggleBold = () => {
    if (!editor.getText().trim()) {
      return editor.chain().focus().setTextSelection(1).setBold().run();
    }
    const chain = editor.chain().focus();
    return (editor.isActive("bold") ? chain.unsetBold() : chain.setBold()).run();
  };

  const tool = (name, active, action, icon, disabled = false) => (
    <button
      type="button"
      className="editor-tool"
      aria-label={name}
      aria-pressed={active}
      disabled={disabled}
      onMouseDown={(event) => {
        event.preventDefault();
        action();
      }}
      onClick={(event) => event.preventDefault()}
    >
      {icon}
    </button>
  );

  return (
    <div className="relative overflow-hidden rounded-panel border border-border bg-surface">
      <div
        className="testing-editor-toolbar"
        role="toolbar"
        aria-label="Công cụ soạn thảo kiểm thử"
      >
        <div className="editor-tool-group">
          {tool("In đậm", editor.isActive("bold"), toggleBold, <Bold size={17} />)}
          {tool(
            "In nghiêng",
            editor.isActive("italic"),
            () => editor.chain().focus().toggleItalic().run(),
            <Italic size={17} />,
          )}
          {tool(
            "Gạch chân",
            editor.isActive("underline"),
            () => editor.chain().focus().toggleUnderline().run(),
            <UnderlineIcon size={17} />,
          )}
          {tool(
            "Gạch ngang",
            editor.isActive("strike"),
            () => editor.chain().focus().toggleStrike().run(),
            <Strikethrough size={17} />,
          )}
          {tool(
            "Mã nội dòng",
            editor.isActive("code"),
            () => editor.chain().focus().toggleCode().run(),
            <Braces size={17} />,
          )}
          {tool(
            "Đánh dấu",
            editor.isActive("highlight"),
            () => editor.chain().focus().toggleHighlight({ color: "#fef08a" }).run(),
            <Highlighter size={17} />,
          )}
          {tool(
            "Chỉ số dưới",
            editor.isActive("subscript"),
            () => editor.chain().focus().toggleSubscript().run(),
            <SubscriptIcon size={17} />,
          )}
          {tool(
            "Chỉ số trên",
            editor.isActive("superscript"),
            () => editor.chain().focus().toggleSuperscript().run(),
            <SuperscriptIcon size={17} />,
          )}
        </div>
        <div className="editor-tool-group">
          {tool(
            "Đoạn văn",
            editor.isActive("paragraph"),
            () => editor.chain().focus().setParagraph().run(),
            <span className="text-sm font-semibold">P</span>,
          )}
          {tool(
            "Tiêu đề cấp 1",
            editor.isActive("heading", { level: 1 }),
            () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
            <Heading1 size={17} />,
          )}
          {tool(
            "Tiêu đề cấp 2",
            editor.isActive("heading", { level: 2 }),
            () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
            <Heading2 size={17} />,
          )}
          {tool(
            "Tiêu đề cấp 3",
            editor.isActive("heading", { level: 3 }),
            () => editor.chain().focus().toggleHeading({ level: 3 }).run(),
            <Heading3 size={17} />,
          )}
          {tool(
            "Trích dẫn",
            editor.isActive("blockquote"),
            () => editor.chain().focus().toggleBlockquote().run(),
            <Quote size={17} />,
          )}
          {tool(
            "Khối mã",
            editor.isActive("codeBlock"),
            () => editor.chain().focus().toggleCodeBlock().run(),
            <Code2 size={17} />,
          )}
        </div>
        <div className="editor-tool-group">
          {tool(
            "Danh sách dấu đầu dòng",
            editor.isActive("bulletList"),
            () => editor.chain().focus().toggleBulletList().run(),
            <List size={17} />,
          )}
          {tool(
            "Danh sách đánh số",
            editor.isActive("orderedList"),
            () => editor.chain().focus().toggleOrderedList().run(),
            <ListOrdered size={17} />,
          )}
          {tool(
            "Danh sách tác vụ",
            editor.isActive("taskList"),
            () => editor.chain().focus().toggleTaskList().run(),
            <ListChecks size={17} />,
          )}
          {tool(
            "Căn trái",
            editor.isActive({ textAlign: "left" }),
            () => editor.chain().focus().setTextAlign("left").run(),
            <AlignLeft size={17} />,
          )}
          {tool(
            "Căn giữa",
            editor.isActive({ textAlign: "center" }),
            () => editor.chain().focus().setTextAlign("center").run(),
            <AlignCenter size={17} />,
          )}
          {tool(
            "Căn phải",
            editor.isActive({ textAlign: "right" }),
            () => editor.chain().focus().setTextAlign("right").run(),
            <AlignRight size={17} />,
          )}
          {tool(
            "Căn đều",
            editor.isActive({ textAlign: "justify" }),
            () => editor.chain().focus().setTextAlign("justify").run(),
            <AlignJustify size={17} />,
          )}
        </div>
        <div className="editor-tool-group">
          {tool("Thêm hoặc sửa liên kết", editor.isActive("link"), addLink, <LinkIcon size={17} />)}
          {tool(
            "Xóa liên kết",
            false,
            () => editor.chain().focus().unsetLink().run(),
            <Unlink size={17} />,
            !editor.isActive("link"),
          )}
          <label className="editor-tool" aria-label="Màu chữ">
            <input
              type="color"
              className="h-5 w-5 cursor-pointer border-0 bg-transparent p-0"
              value={editor.getAttributes("textStyle").color || "#1d1d1f"}
              onChange={(event) => editor.chain().focus().setColor(event.target.value).run()}
            />
          </label>
          <select
            className="editor-select"
            aria-label="Phông chữ"
            value={editor.getAttributes("textStyle").fontFamily || ""}
            onChange={(event) =>
              event.target.value
                ? editor.chain().focus().setFontFamily(event.target.value).run()
                : editor.chain().focus().unsetFontFamily().run()
            }
          >
            <option value="">Mặc định</option>
            <option value="Arial">Arial</option>
            <option value="Georgia">Georgia</option>
            <option value="Times New Roman">Times New Roman</option>
            <option value="Courier New">Courier New</option>
          </select>
        </div>
        <div className="editor-tool-group">
          {tool("Công thức", false, addMath, <Sigma size={17} />)}
          {tool("Emoji", false, addEmoji, <Smile size={17} />)}
          {tool("Nhắc người dùng", false, addMention, <AtSign size={17} />)}
          {tool("Hình ảnh", false, addImage, <ImagePlus size={17} />)}
          {tool("Video YouTube", editor.isActive("youtube"), addYoutube, <YoutubeIcon size={17} />)}
          {tool(
            "Ký tự ẩn",
            false,
            () => editor.chain().focus().toggleInvisibleCharacters().run(),
            <Eye size={17} />,
          )}
          {tool(
            editor.isActive("details") ? "Tháo khối thu gọn" : "Khối thu gọn",
            editor.isActive("details"),
            () =>
              editor.isActive("details")
                ? editor.chain().focus().unsetDetails().run()
                : editor.chain().focus().setDetails().run(),
            <ChevronDownSquare size={17} />,
          )}
          {tool(
            "Đường phân cách",
            false,
            () => editor.chain().focus().setHorizontalRule().run(),
            <Minus size={17} />,
          )}
        </div>
        <div className="editor-tool-group">
          {tool(
            "Chèn bảng",
            editor.isActive("table"),
            () =>
              editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
            <Table2 size={17} />,
          )}
          {tool(
            "Thêm hàng",
            false,
            () => editor.chain().focus().addRowAfter().run(),
            <Rows3 size={17} />,
            !editor.isActive("table"),
          )}
          {tool(
            "Thêm cột",
            false,
            () => editor.chain().focus().addColumnAfter().run(),
            <Columns3 size={17} />,
            !editor.isActive("table"),
          )}
          {tool(
            "Xóa hàng",
            false,
            () => editor.chain().focus().deleteRow().run(),
            <span className="text-xs font-semibold">−R</span>,
            !editor.isActive("table"),
          )}
          {tool(
            "Xóa cột",
            false,
            () => editor.chain().focus().deleteColumn().run(),
            <span className="text-xs font-semibold">−C</span>,
            !editor.isActive("table"),
          )}
          {tool(
            "Xóa bảng",
            false,
            () => editor.chain().focus().deleteTable().run(),
            <Trash2 size={17} />,
            !editor.isActive("table"),
          )}
        </div>
        <div className="editor-tool-group">
          {tool(
            "Hoàn tác",
            false,
            () => editor.chain().focus().undo().run(),
            <Undo2 size={17} />,
            !editor.can().undo(),
          )}
          {tool(
            "Làm lại",
            false,
            () => editor.chain().focus().redo().run(),
            <Redo2 size={17} />,
            !editor.can().redo(),
          )}
        </div>
        <output className="ml-auto px-2 text-[11px] font-medium text-ink-faint" aria-live="polite">
          {editor.storage.characterCount.characters()} ký tự ·{" "}
          {editor.storage.characterCount.words()} từ
        </output>
      </div>
      {tableOfContents.length > 0 && (
        <nav className="testing-table-of-contents" aria-label="Mục lục nội dung">
          <span className="testing-table-of-contents-title">Mục lục</span>
          <ol>
            {tableOfContents.map((item) => (
              <li key={item.id} style={{ paddingLeft: `${Math.max(item.level - 1, 0) * 0.75}rem` }}>
                <button
                  type="button"
                  onClick={() => {
                    editor.commands.setTextSelection(item.pos);
                    editor.commands.scrollIntoView();
                  }}
                >
                  {item.textContent}
                </button>
              </li>
            ))}
          </ol>
        </nav>
      )}
      {!readOnly && (
        <>
          <BubbleMenu editor={editor} className="testing-bubble-menu">
            {tool("In đậm", editor.isActive("bold"), toggleBold, <Bold size={15} />)}
            {tool(
              "In nghiêng",
              editor.isActive("italic"),
              () => editor.chain().focus().toggleItalic().run(),
              <Italic size={15} />,
            )}
            {tool(
              "Đánh dấu",
              editor.isActive("highlight"),
              () => editor.chain().focus().toggleHighlight({ color: "#fef08a" }).run(),
              <Highlighter size={15} />,
            )}
          </BubbleMenu>
          <FloatingMenu editor={editor} className="testing-floating-menu">
            {tool(
              "Tiêu đề cấp 2",
              false,
              () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
              <Heading2 size={15} />,
            )}
            {tool(
              "Danh sách dấu đầu dòng",
              false,
              () => editor.chain().focus().toggleBulletList().run(),
              <List size={15} />,
            )}
            {tool(
              "Danh sách tác vụ",
              false,
              () => editor.chain().focus().toggleTaskList().run(),
              <ListChecks size={15} />,
            )}
          </FloatingMenu>
        </>
      )}
      <EditorContent editor={editor} />
      {dialog}
    </div>
  );
}
