import ReactMarkdown from "react-markdown";
import styles from "./Markdown.module.css";

// react-markdown renders to React elements (no HTML injection) and
// ignores raw HTML by default; its urlTransform drops unsafe link
// targets such as javascript:, so stored admin text is safe here.
export default function Markdown({ text, className }) {
  if (!text) return null;

  return (
    <div
      className={
        className ? `${styles.markdown} ${className}` : styles.markdown
      }
    >
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}
