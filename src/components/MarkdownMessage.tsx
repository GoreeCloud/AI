import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...props }) {
            return <a href={href} target="_blank" rel="noreferrer" {...props}>{children}</a>
          },
          code({ className, children, ...props }) {
            const block = Boolean(className) || String(children).includes('\n')
            return block ? <code className={className} {...props}>{children}</code> : <code className="inline-code" {...props}>{children}</code>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
