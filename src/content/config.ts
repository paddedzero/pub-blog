import { z, defineCollection } from 'astro:content';

const postsCollection = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string(),
        description: z.string().optional(),
        pubDate: z.coerce.date(),
        updatedDate: z.coerce.date().optional(),
        categories: z.array(z.string()).default([]),
        tags: z.array(z.string()).default([]),
        author: z.string().default('feedmeup'),
        aiGenerated: z.boolean().default(false),
    }),
});

const errorsCollection = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string(),
        description: z.string().optional(),
        pubDate: z.coerce.date(),
        categories: z.array(z.string()).default(['error']),
        tags: z.array(z.string()).default(['error']),
        author: z.string().default('feedmeup'),
        aiGenerated: z.boolean().default(false),
    }),
});

export const collections = {
    posts: postsCollection,
    errors: errorsCollection,
};
