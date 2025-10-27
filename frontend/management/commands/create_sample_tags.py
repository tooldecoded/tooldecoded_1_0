from django.core.management.base import BaseCommand
from frontend.models import Tag, LearningArticle

class Command(BaseCommand):
    help = 'Create sample tags and assign them to existing articles'

    def handle(self, *args, **options):
        # Create sample tags
        tags_data = [
            {'name': 'Power Tools', 'color': '#EF4444', 'is_predefined': True},
            {'name': 'Batteries', 'color': '#10B981', 'is_predefined': True},
            {'name': 'Chargers', 'color': '#3B82F6', 'is_predefined': True},
            {'name': 'Safety', 'color': '#F59E0B', 'is_predefined': True},
            {'name': 'Maintenance', 'color': '#8B5CF6', 'is_predefined': True},
            {'name': 'Reviews', 'color': '#EC4899', 'is_predefined': True},
            {'name': 'Tutorials', 'color': '#06B6D4', 'is_predefined': True},
            {'name': 'Comparisons', 'color': '#84CC16', 'is_predefined': True},
        ]
        
        created_tags = []
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'color': tag_data['color'],
                    'is_predefined': tag_data['is_predefined']
                }
            )
            if created:
                self.stdout.write(f'Created tag: {tag.name}')
            else:
                self.stdout.write(f'Tag already exists: {tag.name}')
            created_tags.append(tag)
        
        # Assign tags to existing articles (if any)
        articles = LearningArticle.objects.filter(is_published=True)
        if articles.exists():
            self.stdout.write(f'Found {articles.count()} published articles')
            
            # Assign random tags to articles for demonstration
            for i, article in enumerate(articles):
                # Assign 1-3 random tags to each article
                import random
                num_tags = random.randint(1, 3)
                selected_tags = random.sample(created_tags, min(num_tags, len(created_tags)))
                article.tags.set(selected_tags)
                self.stdout.write(f'Assigned tags to article: {article.title}')
        else:
            self.stdout.write('No published articles found. Create some articles first.')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample tags and assigned them to articles!')
        )
