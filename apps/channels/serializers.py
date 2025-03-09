from rest_framework import serializers
from .models import Stream, Channel, ChannelGroup, ChannelStream
from core.models import StreamProfile

#
# Stream
#
class StreamSerializer(serializers.ModelSerializer):
    stream_profile_id = serializers.PrimaryKeyRelatedField(
        queryset=StreamProfile.objects.all(),
        source='stream_profile',
        allow_null=True,
        required=False
    )

    class Meta:
        model = Stream
        fields = [
            'id',
            'name',
            'url',
            'custom_url',
            'm3u_account',  # Uncomment if using M3U fields
            'logo_url',
            'tvg_id',
            'local_file',
            'current_viewers',
            'updated_at',
            'group_name',
            'stream_profile_id',
        ]

    def get_fields(self):
        fields = super().get_fields()

        # Unable to edit specific properties if this stream was created from an M3U account
        if self.instance and getattr(self.instance, 'm3u_account', None):
            fields['id'].read_only = True
            fields['name'].read_only = True
            fields['url'].read_only = True
            fields['m3u_account'].read_only = True
            fields['tvg_id'].read_only = True
            fields['group_name'].read_only = True

        return fields


#
# Channel Group
#
class ChannelGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelGroup
        fields = ['id', 'name']


#
# Channel
#
class ChannelSerializer(serializers.ModelSerializer):
    # Show nested group data, or ID
    channel_group = ChannelGroupSerializer(read_only=True)
    channel_group_id = serializers.PrimaryKeyRelatedField(
        queryset=ChannelGroup.objects.all(),
        source="channel_group",
        write_only=True,
        required=False
    )

    stream_profile_id = serializers.PrimaryKeyRelatedField(
        queryset=StreamProfile.objects.all(),
        source='stream_profile',
        allow_null=True,
        required=False
    )

    streams = serializers.SerializerMethodField()
    stream_ids = serializers.PrimaryKeyRelatedField(
        queryset=Stream.objects.all(), many=True, write_only=True, required=False
    )

    class Meta:
        model = Channel
        fields = [
            'id',
            'channel_number',
            'channel_name',
            'logo_url',
            'logo_file',
            'channel_group',
            'channel_group_id',
            'tvg_id',
            'tvg_name',
            'streams',
            'stream_ids',
            'stream_profile_id',
        ]

    def get_streams(self, obj):
        """Retrieve ordered stream objects for GET requests."""
        ordered_streams = obj.streams.all().order_by('channelstream__order')
        print(f'Retrieving streams in order')
        for index, stream in enumerate(ordered_streams):
            print(f'Stream {stream.id}, index {index}')
        return StreamSerializer(ordered_streams, many=True).data

    # def get_stream_ids(self, obj):
    #     """Retrieve ordered stream IDs for GET requests."""
    #     return list(obj.streams.all().order_by('channelstream__order').values_list('id', flat=True))

    def create(self, validated_data):
        stream_ids = validated_data.pop('streams', [])
        channel = Channel.objects.create(**validated_data)

        # Add streams in the specified order
        for index, stream_id in enumerate(stream_ids):
            ChannelStream.objects.create(channel=channel, stream_id=stream_id, order=index)

        return channel

    def update(self, instance, validated_data):
        print("Validated Data:", validated_data)
        streams = validated_data.pop('stream_ids', None)
        print(f'stream ids: {streams}')

        # Update the actual Channel fields
        instance.channel_number = validated_data.get('channel_number', instance.channel_number)
        instance.channel_name = validated_data.get('channel_name', instance.channel_name)
        instance.logo_url = validated_data.get('logo_url', instance.logo_url)
        instance.tvg_id = validated_data.get('tvg_id', instance.tvg_id)
        instance.tvg_name = validated_data.get('tvg_name', instance.tvg_name)

        # If serializer allows changing channel_group or stream_profile:
        if 'channel_group' in validated_data:
            instance.channel_group = validated_data['channel_group']
        if 'stream_profile' in validated_data:
            instance.stream_profile = validated_data['stream_profile']

        instance.save()

        # Handle the many-to-many 'streams'
        if streams is not None:
            # Clear existing relationships
            instance.channelstream_set.all().delete()
            # Add new streams in order
            for index, stream in enumerate(streams):
                print(f'Setting stream {stream.id} to index {index}')
                ChannelStream.objects.create(channel=instance, stream_id=stream.id, order=index)

        return instance
