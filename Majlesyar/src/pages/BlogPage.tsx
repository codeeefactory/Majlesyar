import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { BookOpen, CalendarDays, Clock, Eye, RefreshCw, Search, Tag, X } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SEO } from "@/components/SEO";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { listBlogCategories, listBlogPosts, listBlogTags } from "@/lib/api";
import type { BlogCategory, BlogPost, BlogTag } from "@/types/domain";

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

function BlogPostCard({ post, featured = false }: { post: BlogPost; featured?: boolean }) {
  return (
    <Card className="overflow-hidden rounded-lg border-border/70 bg-card shadow-soft transition-shadow hover:shadow-medium">
      <Link to={`/blog/${post.slug}`} className={featured ? "md:grid md:grid-cols-[1.1fr_1fr]" : "block"}>
        <div className={`bg-muted ${featured ? "aspect-[16/10] md:aspect-auto md:min-h-full" : "aspect-[16/10]"}`}>
          {post.heroImage ? (
            <img
              src={post.heroImage}
              alt={post.heroImageAlt}
              className="h-full w-full object-cover"
              loading={featured ? "eager" : "lazy"}
              decoding="async"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/10 via-background to-accent/15">
              <BookOpen className="h-12 w-12 text-primary" aria-hidden="true" />
            </div>
          )}
        </div>
        <CardContent className="space-y-4 p-5 md:p-6">
          <div className="flex flex-wrap items-center gap-2">
            {post.category ? <Badge variant="secondary">{post.category.name}</Badge> : null}
            {post.featured ? <Badge>ویژه</Badge> : null}
          </div>
          <div className="space-y-2">
            <h2 className={`${featured ? "text-2xl md:text-3xl" : "text-xl"} font-bold leading-8 text-foreground`}>
              {post.title}
            </h2>
            <p className="line-clamp-3 text-sm leading-7 text-muted-foreground">
              {post.excerpt || post.subtitle}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              {formatDate(post.publishedAt)}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-4 w-4" aria-hidden="true" />
              {post.readingMinutes.toLocaleString("fa-IR")} دقیقه
            </span>
            <span className="inline-flex items-center gap-1">
              <Eye className="h-4 w-4" aria-hidden="true" />
              {post.viewCount.toLocaleString("fa-IR")}
            </span>
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}

export default function BlogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const activeCategory = searchParams.get("category") || "";
  const activeTag = searchParams.get("tag") || "";
  const activeSearch = searchParams.get("search") || "";

  useEffect(() => {
    setSearch(activeSearch);
  }, [activeSearch]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError("");
    Promise.all([
      listBlogPosts({ category: activeCategory, tag: activeTag, search: activeSearch }),
      listBlogCategories(),
      listBlogTags(),
    ])
      .then(([postsData, categoriesData, tagsData]) => {
        if (!mounted) return;
        setPosts(postsData);
        setCategories(categoriesData);
        setTags(tagsData);
      })
      .catch(() => {
        if (!mounted) return;
        setPosts([]);
        setError("دریافت مقاله ها انجام نشد. دوباره تلاش کنید.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [activeCategory, activeTag, activeSearch, reloadKey]);

  const featuredPost = useMemo(() => posts.find((post) => post.featured) || posts[0], [posts]);
  const regularPosts = useMemo(
    () => (featuredPost ? posts.filter((post) => post.id !== featuredPost.id) : posts),
    [featuredPost, posts],
  );

  function updateFilter(next: { category?: string; tag?: string; search?: string }) {
    const params = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
    setSearchParams(params);
  }

  function resetFilters() {
    setSearch("");
    setSearchParams({});
  }

  return (
    <AppShell>
      <SEO
        title="مجله مجلس یار"
        description="مقاله های تخصصی درباره پذیرایی، پک مراسم، گل آرایی، حلوا و خرما و برگزاری بهتر مراسم."
        path="/blog"
        keywords={["وبلاگ مجلس یار", "مقالات پذیرایی", "راهنمای مراسم", "پک پذیرایی"]}
      />
      <div className="container py-8 md:py-12">
        <div className="mb-8 grid gap-6 lg:grid-cols-[1fr_320px] lg:items-end">
          <div className="space-y-4">
            <Badge variant="secondary" className="w-fit gap-2">
              <BookOpen className="h-4 w-4" aria-hidden="true" />
              مجله مجلس یار
            </Badge>
            <h1 className="text-3xl font-bold leading-10 text-foreground md:text-4xl">
              راهنماها و مقاله های کاربردی برای مراسم بهتر
            </h1>
            <p className="max-w-3xl text-muted-foreground leading-8">
              از انتخاب پک پذیرایی و فینگرفود تا گل آرایی، حلوا و خرما و نکته های اجرایی مراسم را اینجا بخوانید.
            </p>
          </div>
          <form
            className="flex gap-2"
            toolname="search_blog_posts"
            tooldescription="Search Majlesyar blog posts by keyword."
            onSubmit={(event) => {
              event.preventDefault();
              updateFilter({ search: search.trim() });
            }}
          >
            <Input
              name="search"
              toolparamdescription="Keyword used to filter blog posts."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="جستجو در مقاله ها"
            />
            <Button type="submit" size="icon" aria-label="جستجو">
              <Search className="h-5 w-5" aria-hidden="true" />
            </Button>
          </form>
        </div>

        <div className="mb-8 flex flex-wrap gap-2">
          <Button variant={!activeCategory && !activeTag && !activeSearch ? "default" : "outline"} size="sm" onClick={resetFilters} aria-pressed={!activeCategory && !activeTag && !activeSearch}>
            همه مقاله ها
          </Button>
          {categories.map((category) => (
            <Button
              key={category.id}
              variant={activeCategory === category.slug ? "default" : "outline"}
              size="sm"
              onClick={() => updateFilter({ category: activeCategory === category.slug ? "" : category.slug, tag: "" })}
              aria-pressed={activeCategory === category.slug}
            >
              {category.name}
              <span className="text-xs opacity-70">{category.postCount.toLocaleString("fa-IR")}</span>
            </Button>
          ))}
        </div>

        {tags.length ? (
          <div className="mb-8 flex flex-wrap items-center gap-2 text-sm">
            <Tag className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            {tags.slice(0, 12).map((tag) => (
              <button
                type="button"
                key={tag.id}
                onClick={() => updateFilter({ tag: activeTag === tag.slug ? "" : tag.slug })}
                aria-pressed={activeTag === tag.slug}
                className={`rounded-full border px-3 py-1 transition-colors ${
                  activeTag === tag.slug
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                {tag.name}
                <span className="mr-1 text-xs opacity-70">{tag.postCount.toLocaleString("fa-IR")}</span>
              </button>
            ))}
          </div>
        ) : null}

        {activeSearch || activeCategory || activeTag ? (
          <div className="mb-6 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{posts.length.toLocaleString("fa-IR")} نتیجه</span>
            {activeSearch ? <Badge variant="secondary">جستجو: {activeSearch}</Badge> : null}
            <Button type="button" variant="ghost" size="sm" className="h-8 gap-1" onClick={resetFilters}>
              <X className="h-4 w-4" aria-hidden="true" />
              پاک کردن فیلترها
            </Button>
          </div>
        ) : null}

        {loading ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-72 rounded-lg" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/30 bg-card p-8 text-center">
            <p className="mb-4 text-muted-foreground">{error}</p>
            <Button type="button" variant="outline" className="gap-2" onClick={() => setReloadKey((value) => value + 1)}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              تلاش دوباره
            </Button>
          </div>
        ) : posts.length ? (
          <div className="space-y-6">
            {featuredPost ? <BlogPostCard post={featuredPost} featured /> : null}
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {regularPosts.map((post) => (
                <BlogPostCard key={post.id} post={post} />
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
            <p className="mb-4">مقاله ای پیدا نشد.</p>
            <Button type="button" variant="outline" onClick={resetFilters}>
              نمایش همه مقاله ها
            </Button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
