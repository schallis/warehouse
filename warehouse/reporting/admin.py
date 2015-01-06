from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from reporting import models


from django.contrib import admin
from django.contrib.admin.util import flatten_fieldsets

class CustomAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields

        if self.declared_fieldsets:
            return flatten_fieldsets(self.declared_fieldsets)
        else:
            return list(set(
                [field.name for field in self.opts.local_fields] +
                [field.name for field in self.opts.local_many_to_many]
            ))

class ShapeInline(admin.TabularInline):
    model = models.Shape
    fields = ('link', 'shapetag', 'size')
    readonly_fields = ('link', 'shapetag', 'size')

    def link(self, instance):
        url = reverse("admin:reporting_shape_change", args = (instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.vs_id))


class AssetAdmin(CustomAdmin):
    list_display = ('vs_id', 'username', 'all_sites')

    inlines = ShapeInline,

    def all_sites(self, obj):
        return ", ".join([site.name for site in obj.sites.all()])


class ShapeAdmin(admin.ModelAdmin):
    list_display = ('vs_id', 'shapetag', 'size', 'version', 'item')


admin.site.register(models.Asset, AssetAdmin)
admin.site.register(models.Shape, ShapeAdmin)
admin.site.register(models.Download)

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(Site)
