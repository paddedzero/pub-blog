import { SITE } from '@/config';

export function getWebSiteSchema(url: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: SITE.title,
    description: SITE.desc,
    url: url,
    author: {
      '@type': 'Person',
      name: SITE.author,
    },
    inLanguage: SITE.lang,
  };
}

export function getBlogPostingSchema(data: {
  title: string;
  description: string;
  pubDate: Date;
  url: string;
  lang?: string;
  image?: string;
  tags?: string[];
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: data.title,
    description: data.description,
    datePublished: data.pubDate.toISOString(),
    dateModified: data.pubDate.toISOString(),
    author: {
      '@type': 'Person',
      name: SITE.author,
    },
    publisher: {
      '@type': 'Organization',
      name: SITE.title,
      logo: {
        '@type': 'ImageObject',
        url: `${SITE.website}/${SITE.ogImage}`,
      },
    },
    url: data.url,
    image: data.image,
    keywords: data.tags?.join(', '),
    inLanguage: data.lang || SITE.lang,
  };
}

export function getPersonSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Person',
    name: SITE.author,
    url: SITE.website,
    sameAs: Object.values(SITE.social),
  };
}

export function getBreadcrumbSchema(items: { name: string; url: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

export function getOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: SITE.title,
    url: SITE.website,
    logo: {
      '@type': 'ImageObject',
      url: `${SITE.website}/${SITE.ogImage}`,
    },
    sameAs: Object.values(SITE.social),
  };
}
