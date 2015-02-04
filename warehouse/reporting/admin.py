from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum

from reporting import models


from django.contrib import admin
from django.contrib.admin.util import flatten_fieldsets

class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if self.declared_fieldsets:
            return flatten_fieldsets(self.declared_fieldsets)
        else:
            return list(set(
                [field.name for field in self.opts.local_fields] +
                [field.name for field in self.opts.local_many_to_many]
            ))


class ShapeInline(admin.TabularInline):
    model = models.Shape
    fields = ('link', 'shapetag', 'size', 'sync_uuid')
    readonly_fields = ('link', 'shapetag', 'size')
    extra = 0

    def link(self, instance):
        url = reverse("admin:reporting_shape_change", args = (instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.vs_id))


class AssetAdmin(ReadOnlyAdmin):
    actions = None
    inlines = ShapeInline,
    list_display = ('vs_id', 'username', 'all_sites', 'storage_size',
            'sync_uuid')

    def storage_size(self, asd):
        total_bytes = asd.shape_set.aggregate(Sum('size'))['size__sum'] or 0
        return '{:.2}'.format(float(total_bytes)/1000**3)

    storage_size.short_description = 'Storage Size (GB)'

    def all_sites(self, obj):
        return ", ".join([site.name for site in obj.sites.all()])


class ShapeAdmin(ReadOnlyAdmin):
    list_display = ('vs_id', 'shapetag', 'size', 'version', 'item')
    actions = None



admin.site.register(models.Asset, AssetAdmin)
admin.site.register(models.Shape, ShapeAdmin)
admin.site.register(models.Download)

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(Site)
