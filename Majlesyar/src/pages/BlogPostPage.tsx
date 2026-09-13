import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { CalendarDays, Clock, Eye, Link2, ListTree, MessageCircle, RefreshCw, Send } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SEO } from "@/components/SEO";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { createBlogComment, getBlogPost } from "@/lib/api";
import { notifyError, notifySuccess } from "@/lib/notify";
import type { BlogComment, BlogPost } from "@/types/domain";

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

function headingId(text: string) {
  return text
    .trim()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .replace(/\s+/g, "-")
    .toLowerCase();
}

function renderContent(content: string) {
  return content
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block, index) => {
      if (block.startsWith("## ")) {
        const text = block.replace(/^##\s+/, "");
        return (
          <h2 id={headingId(text)} key={index} className="scroll-mt-24 pt-3 text-2xl font-bold leading-9 text-foreground">
            {text}
          </h2>
        );
      }
      if (block.startsWith("### ")) {
        const text = block.replace(/^###\s+/, "");
        return (
          <h3 id={headingId(text)} key={index} className="scroll-mt-24 pt-2 text-xl font-semibold leading-8 text-foreground">
            {text}
          </h3>
        );
      }
      if (block.startsWith("> ")) {
        return (
          <blockquote key={index} className="border-r-4 border-primary/60 bg-muted/50 px-4 py-3 text-base leading-9 text-foreground">
            {block.replace(/^>\s+/gm, "")}
          </blockquote>
        );
      }
      if (/^[-*]\s+/m.test(block)) {
        return (
          <ul key={index} className="list-inside list-disc space-y-2 text-base leading-9 text-muted-foreground">
            {block.split("\n").map((item, itemIndex) => (
              <li key={itemIndex}>{item.replace(/^[-*]\s+/, "")}</li>
            ))}
          </ul>
        );
      }
      if (/^\d+\.\s+/m.test(block)) {
        return (
          <ol key={index} className="list-inside list-decimal space-y-2 text-base leading-9 text-muted-foreground">
            {block.split("\n").map((item, itemIndex) => (
              <li key={itemIndex}>{item.replace(/^\d+\.\s+/, "")}</li>
            ))}
          </ol>
        );
      }
      return (
        <p key={index} className="text-base leading-9 text-muted-foreground">
          {block}
        </p>
      );
    });
}

function CommentItem({ comment }: { comment: BlogComment }) {
  return (
    <div className="rounded-lg border border-border bg-background p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <strong className="text-foreground">{comment.name}</strong>
        <span className="text-xs text-muted-foreground">{formatDate(comment.createdAt)}</span>
      </div>
      <p className="leading-8 text-muted-foreground">{comment.body}</p>
      {comment.replies.length ? (
        <div className="mt-4 space-y-3 border-r border-border pr-4">
          {comment.replies.map((reply) => (
            <CommentItem key={reply.id} comment={reply} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function BlogPostPage() {
  const { slug = "" } = useParams();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [commentForm, setCommentForm] = useState({ name: "", email: "", body: "" });
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError("");
    getBlogPost(slug)
      .then((data) => {
        if (mounted) setPost(data);
      })
      .catch(() => {
        if (!mounted) return;
        setPost(null);
        setError("دریافت مقاله انجام نشد. دوباره تلاش کنید.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [slug, reloadKey]);

  const breadcrumbs = useMemo(
    () => [
      { name: "خانه", url: "/" },
      { name: "مجله", url: "/blog" },
      { name: post?.title || "مقاله", url: `/blog/${slug}` },
    ],
    [post?.title, slug],
  );

  const headings = useMemo(() => {
    return (post?.content || "")
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter((block) => block.startsWith("## "))
      .map((block) => {
        const title = block.replace(/^##\s+/, "");
        return { id: headingId(title), title };
      })
      .slice(0, 6);
  }, [post?.content]);

  async function copyLink() {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      notifySuccess("لینک مقاله کپی شد.");
    } catch {
      notifyError("کپی لینک انجام نشد.");
    }
  }

  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!post) return;
    setSubmitting(true);
    try {
      const response = await createBlogComment(post.slug, commentForm);
      notifySuccess(response.detail);
      setCommentForm({ name: "", email: "", body: "" });
    } catch {
      notifyError("ثبت دیدگاه انجام نشد. دوباره تلاش کنید.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="container py-8 md:py-12">
          <Skeleton className="mb-6 h-10 w-2/3" />
          <Skeleton className="mb-8 h-80 rounded-lg" />
          <div className="space-y-4">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-11/12" />
            <Skeleton className="h-6 w-10/12" />
          </div>
        </div>
      </AppShell>
    );
  }

  if (!post) {
    return (
      <AppShell>
        <SEO title="مقاله پیدا نشد" path={`/blog/${slug}`} noindex />
        <div className="container py-16 text-center">
          <h1 className="mb-4 text-3xl font-bold text-foreground">{error || "مقاله پیدا نشد"}</h1>
          <div className="flex flex-wrap justify-center gap-3">
            {error ? (
              <Button type="button" variant="outline" className="gap-2" onClick={() => setReloadKey((value) => value + 1)}>
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                تلاش دوباره
              </Button>
            ) : null}
            <Button asChild>
              <Link to="/blog">بازگشت به مجله</Link>
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <SEO
        title={post.seoTitle || post.title}
        description={post.seoDescription || post.excerpt || post.subtitle}
        path={`/blog/${post.slug}`}
        ogImage={post.heroImage}
        keywords={post.seoKeywords}
        breadcrumbs={breadcrumbs}
      />
      <article className="container py-8 md:py-12">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <Link to="/blog">
              <Badge variant="secondary">مجله مجلس یار</Badge>
            </Link>
            {post.category ? <Badge variant="outline">{post.category.name}</Badge> : null}
            {post.tags.slice(0, 4).map((tag) => (
              <Link key={tag.id} to={`/blog?tag=${encodeURIComponent(tag.slug)}`}>
                <Badge variant="outline">{tag.name}</Badge>
              </Link>
            ))}
          </div>

          <header className="mb-8 space-y-4">
            <h1 className="text-3xl font-bold leading-[1.7] text-foreground md:text-5xl">{post.title}</h1>
            {post.subtitle ? <p className="text-lg leading-9 text-muted-foreground">{post.subtitle}</p> : null}
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="h-4 w-4" aria-hidden="true" />
                {formatDate(post.publishedAt)}
              </span>
              <span className="inline-flex items-center gap-1">
                <Clock className="h-4 w-4" aria-hidden="true" />
                {post.readingMinutes.toLocaleString("fa-IR")} دقیقه مطالعه
              </span>
              <span className="inline-flex items-center gap-1">
                <Eye className="h-4 w-4" aria-hidden="true" />
                {post.viewCount.toLocaleString("fa-IR")} بازدید
              </span>
              <Button type="button" variant="ghost" size="sm" className="h-8 gap-1 px-2" onClick={copyLink}>
                <Link2 className="h-4 w-4" aria-hidden="true" />
                کپی لینک
              </Button>
            </div>
          </header>

          {post.heroImage ? (
            <img
              src={post.heroImage}
              alt={post.heroImageAlt}
              className="mb-8 aspect-[16/9] w-full rounded-lg object-cover"
              loading="eager"
              decoding="async"
            />
          ) : null}

          {headings.length ? (
            <nav className="mb-8 rounded-lg border border-border bg-card p-4" aria-label="فهرست مقاله">
              <div className="mb-3 flex items-center gap-2 font-semibold text-foreground">
                <ListTree className="h-5 w-5 text-primary" aria-hidden="true" />
                فهرست مقاله
              </div>
              <div className="flex flex-wrap gap-2">
                {headings.map((heading) => (
                  <a key={heading.id} href={`#${heading.id}`} className="rounded-full border border-border px-3 py-1 text-sm text-muted-foreground hover:text-foreground">
                    {heading.title}
                  </a>
                ))}
              </div>
            </nav>
          ) : null}

          <div className="space-y-5">{renderContent(post.content || "")}</div>

          {post.relatedPosts?.length ? (
            <section className="mt-12">
              <h2 className="mb-4 text-2xl font-bold text-foreground">مقاله های مرتبط</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {post.relatedPosts.map((related) => (
                  <Card key={related.id} className="rounded-lg">
                    <Link to={`/blog/${related.slug}`}>
                      <CardContent className="space-y-3 p-4">
                        <h3 className="font-semibold leading-7 text-foreground">{related.title}</h3>
                        <p className="line-clamp-3 text-sm leading-7 text-muted-foreground">{related.excerpt}</p>
                      </CardContent>
                    </Link>
                  </Card>
                ))}
              </div>
            </section>
          ) : null}

          <section className="mt-12 space-y-5">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 className="text-2xl font-bold text-foreground">دیدگاه ها</h2>
            </div>

            {post.comments?.length ? (
              <div className="space-y-3">
                {post.comments.map((comment) => (
                  <CommentItem key={comment.id} comment={comment} />
                ))}
              </div>
            ) : (
              <p className="rounded-lg border border-border bg-card p-4 text-muted-foreground">
                هنوز دیدگاهی برای این مقاله ثبت نشده است.
              </p>
            )}

            {post.allowComments ? (
              <form
                onSubmit={submitComment}
                className="rounded-lg border border-border bg-card p-5"
                toolname="submit_blog_comment"
                tooldescription="Submit a public comment for a Majlesyar blog post."
              >
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    name="commentName"
                    toolparamdescription="Required public display name for comment."
                    value={commentForm.name}
                    onChange={(event) => setCommentForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="نام"
                    required
                  />
                  <Input
                    name="commentEmail"
                    toolparamdescription="Optional email for comment moderation contact; not displayed publicly."
                    value={commentForm.email}
                    onChange={(event) => setCommentForm((current) => ({ ...current, email: event.target.value }))}
                    placeholder="ایمیل اختیاری"
                    type="email"
                  />
                </div>
                <Textarea
                  name="commentBody"
                  toolparamdescription="Required comment text, maximum 2000 characters."
                  value={commentForm.body}
                  onChange={(event) => setCommentForm((current) => ({ ...current, body: event.target.value }))}
                  placeholder="دیدگاه شما"
                  className="mt-3 min-h-32"
                  maxLength={2000}
                  required
                />
                <div className="mt-2 text-left text-xs text-muted-foreground">
                  {commentForm.body.length.toLocaleString("fa-IR")} / ۲٬۰۰۰
                </div>
                <Button type="submit" className="mt-3 gap-2" disabled={submitting || commentForm.name.trim().length < 1 || commentForm.body.trim().length < 3}>
                  <Send className="h-4 w-4" aria-hidden="true" />
                  {submitting ? "در حال ثبت..." : "ثبت دیدگاه"}
                </Button>
              </form>
            ) : null}
          </section>
        </div>
      </article>
    </AppShell>
  );
}
