import rss from '@astrojs/rss';
import type { CollectionEntry } from 'astro:content';
import { SITE } from '@/config';
import type { APIContext } from 'astro';
import { getPublishedPosts, getPostSlug, getPublishedNewsfeed, getNewsfeedSlug } from '@/lib/utils/posts';

export async function GET(context: APIContext) {
  const posts = await getPublishedPosts();
  const newsfeed = await getPublishedNewsfeed();

  const allPosts = [
    ...posts.map((post: CollectionEntry<'posts'>) => ({
      ...post.data,
      link: `/posts/${getPostSlug(post)}/`,
    })),
    ...newsfeed.map((post: CollectionEntry<'newsfeed'>) => ({
      ...post.data,
      link: `/posts/${getNewsfeedSlug(post)}/`,
    }))
  ];

  // Sort posts by date (newest first)
  const sortedPosts = allPosts.sort((a, b) => b.pubDate.valueOf() - a.pubDate.valueOf());

  return rss({
    title: SITE.title,
    description: SITE.desc,
    site: context.site || SITE.website,
    items: sortedPosts.map((post) => ({
      title: post.title,
      pubDate: post.pubDate,
      description: post.description,
      link: post.link,
      categories: post.tags,
    })),
    customData: `<language>en-us</language>`,
  });
}
