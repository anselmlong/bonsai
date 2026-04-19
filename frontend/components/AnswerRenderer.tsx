"use client";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import styles from "./AnswerRenderer.module.css";

interface Citation {
  n: number;
  title: string;
  url: string;
}

function extractCitations(markdown: string): Map<string, Citation> {
  const map = new Map<string, Citation>();
  const linkRe = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  let match;
  let n = 1;
  while ((match = linkRe.exec(markdown)) !== null) {
    const [, title, url] = match;
    if (!map.has(url)) {
      map.set(url, { n: n++, title, url });
    }
  }
  return map;
}

interface Props {
  content: string;
}

export function AnswerRenderer({ content }: Props) {
  const citations = extractCitations(content);

  const components: Components = {
    h2({ children }) {
      return <h2 className={styles.h2}>{children}</h2>;
    },
    h3({ children }) {
      return <h3 className={styles.h3}>{children}</h3>;
    },
    a({ href, children }) {
      const citation = href ? citations.get(href) : undefined;
      if (citation) {
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.citationLink}
            title={citation.title}
          >
            <sup className={styles.citationMark}>[{citation.n}]</sup>
          </a>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className={styles.plainLink}>
          {children}
        </a>
      );
    },
  };

  return (
    <div className={styles.root}>
      <ReactMarkdown components={components}>{content}</ReactMarkdown>
      {citations.size > 0 && (
        <section className={styles.references}>
          <div className={styles.referencesLabel}>Sources</div>
          <ol className={styles.referenceList}>
            {[...citations.values()].map((c) => (
              <li key={c.url} className={styles.reference}>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.refLink}
                >
                  {c.title}
                </a>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
