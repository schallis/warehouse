from django.contrib import admin
from django.contrib.auth.models import User, Group
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
    fields = ('link', 'shapetag', 'size')
    readonly_fields = ('link', 'shapetag', 'size')
    extra = 0

    def link(self, instance):
        url = reverse("admin:reporting_shape_change", args = (instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.vs_id))


class AssetAdmin(ReadOnlyAdmin):
    actions = None
    inlines = ShapeInline,
    fields = ('vs_id', 'username', 'filename', 'created', 'deleted',
            'raw_data', 'last_synced', 'last_sync', 'id', 'storage_size')
    list_display = ('vs_id', 'username', 'last_sync')

    #WARNING: Both of the below execute SQL for *each row* and are slow

    def storage_size(self, obj):
        total_bytes = obj.shape_set.aggregate(Sum('size'))['size__sum'] or 0
        return '{:.2f}'.format(float(total_bytes)/1000**3)

    storage_size.short_description = 'Storage Size (GB)'

    def all_sites(self, obj):
        return ", ".join([site.domain for site in obj.sites.all()])


class ShapeAdmin(ReadOnlyAdmin):
    fields = ('vs_id', 'deleted', 'timestamp', 'last_synced', 'last_sync',
            'asset', 'version', 'raw_data', 'shapetag', 'size')
    list_display = ('vs_id', 'shapetag', 'size', 'version', 'asset',
            'last_sync')
    actions = None


class AssetInline(admin.TabularInline):
    model = models.Asset
    fields = ('vs_id', 'username', 'sites')
    readonly_fields = ('vs_id', 'username', 'sites')
    extra = 0

    def link(self, instance):
        url = reverse("admin:reporting_asset_change", args = (instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.vs_id))


class SyncRunAdmin(ReadOnlyAdmin):
    list_display = ('sync_uuid', 'start_time', 'end_time', 'completed',
            'remaining')
    actions = None
    #inlines = AssetInline,

    def remaining(self, obj):
        return obj.asset_set.count()


admin.site.register(models.Asset, AssetAdmin)
admin.site.register(models.Shape, ShapeAdmin)
admin.site.register(models.Download)
admin.site.register(models.SyncRun, SyncRunAdmin)
admin.site.register(models.Site)

#admin.site.unregister(User)
admin.site.unregister(Group)
#admin.site.unregister(Site)
