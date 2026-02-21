import { getPublishedPosts, getPostSlug, getPublishedNewsfeed, getNewsfeedSlug } from '@/lib/utils/posts';

export const GET = async () => {
  const posts = await getPublishedPosts();
  const newsfeed = await getPublishedNewsfeed();

  const searchIndex = [
    ...posts.map((post) => ({
      id: getPostSlug(post),
      data: {
        title: post.data.title,
        description: post.data.description,
      },
    })),
    ...newsfeed.map((post) => ({
      id: getNewsfeedSlug(post),
      data: {
        title: post.data.title,
        description: post.data.description,
      },
    })),
  ];

  return new Response(JSON.stringify(searchIndex), {
    headers: {
      'Content-Type': 'application/json',
    },
  });
};
