import React, { useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Avatar } from './ui/avatar';
import { Card } from './ui/card';
import { Instagram, Facebook, ExternalLink, MessageCircle, Send } from 'lucide-react';

const formatTimestamp = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return date.toLocaleString();
};

const PostPreview = ({ post }) => {
  if (!post) return null;

  const isVideo = post.media_type === 'VIDEO' || post.media_type === 'REEL';

  return (
    <Card className="bg-[#1a1a2e] border border-gray-800 overflow-hidden mb-3">
      <div className="flex items-start gap-3 p-4 border-b border-gray-800">
        <Avatar className="w-10 h-10">
          <img
            src={post.profile_pic || `https://ui-avatars.com/api/?name=${post.username || 'IG'}`}
            alt={post.username || 'Post Author'}
          />
        </Avatar>
        <div className="flex-1">
          <p className="text-white font-semibold">{post.username || 'Unknown'}</p>
          <p className="text-xs text-gray-400">{formatTimestamp(post.timestamp)}</p>
        </div>
        {post.permalink && (
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-400 hover:text-gray-200"
            onClick={() => window.open(post.permalink, '_blank')}
            aria-label="Open post in new tab"
          >
            <ExternalLink className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="relative aspect-square bg-black/30">
        {isVideo ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-300">
            <MessageCircle className="h-10 w-10 opacity-50" />
          </div>
        ) : (
          <img src={post.media_url} alt={post.caption || 'Post media'} className="w-full h-full object-cover" />
        )}
      </div>
      {post.caption && (
        <div className="p-4 border-t border-gray-800">
          <p className="text-sm text-gray-200 whitespace-pre-line">{post.caption}</p>
        </div>
      )}
    </Card>
  );
};

const CommentListItem = ({ comment, isActive, onSelect }) => {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left rounded-xl border border-transparent px-3 py-3 transition-colors ${
        isActive ? 'bg-gradient-to-r from-purple-600/10 to-pink-600/10 border-purple-500/50' : 'hover:bg-[#1f1f2f]'
      }`}
    >
      <div className="flex items-center gap-3">
        <Avatar className="w-10 h-10 shrink-0">
          <img
            src={comment.profile_pic || `https://ui-avatars.com/api/?name=${comment.username}`}
            alt={comment.username}
          />
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-white truncate">{comment.username}</p>
            <span className="text-[11px] text-gray-500 whitespace-nowrap">{formatTimestamp(comment.timestamp)}</span>
          </div>
          <p className="mt-1 text-xs text-gray-400 truncate">{comment.text || 'No comment text'}</p>
        </div>
      </div>
    </button>
  );
};

const ThreadMessage = ({ username, text, timestamp, align = 'left' }) => {
  const isRight = align === 'right';

  return (
    <div className={`flex ${isRight ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 border border-gray-800 ${
          isRight ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white' : 'bg-[#1a1a2e] text-gray-200'
        }`}
      >
        <p className={`text-xs font-semibold ${isRight ? 'text-purple-100' : 'text-gray-300'}`}>{username}</p>
        <p className="mt-1 text-sm whitespace-pre-line">{text}</p>
        <p className={`mt-2 text-[11px] ${isRight ? 'text-purple-100/70' : 'text-gray-500'}`}>{formatTimestamp(timestamp)}</p>
      </div>
    </div>
  );
};

const SocialComments = ({ selectedPlatform = 'all' }) => {
  const [activeTab, setActiveTab] = useState(selectedPlatform === 'all' ? 'instagram' : selectedPlatform);
  const [comments, setComments] = useState({ instagram: [], facebook: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedThread, setSelectedThread] = useState(null);
  const [replyTarget, setReplyTarget] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [search, setSearch] = useState('');

  const fetchComments = useCallback(async (platform) => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const headers = { Authorization: `Bearer ${token}` };

      const normalize = (list = []) =>
        list.map((item) => ({
          ...item,
          username: item.username || 'Unknown',
          text: item.text || '',
          post: item.post
            ? {
                ...item.post,
                username: item.post.username || item.username || 'Unknown',
                profile_pic: item.post.profile_pic || item.profile_pic || null
              }
            : null,
          replies: (item.replies || []).map((reply) => ({
            ...reply,
            username: reply.username || 'Unknown',
            text: reply.text || '',
            timestamp: reply.timestamp
          }))
        }));

      if (platform === 'all') {
        const [instagramRes, facebookRes] = await Promise.all([
          axios.get(`${API}/instagram/comments`, { headers }),
          axios.get(`${API}/facebook/comments`, { headers })
        ]);
        setComments({
          instagram: normalize(instagramRes.data),
          facebook: normalize(facebookRes.data)
        });
      } else {
        const response = await axios.get(`${API}/${platform}/comments`, { headers });
        setComments((prev) => ({
          ...prev,
          [platform]: normalize(response.data)
        }));
      }
    } catch (err) {
      console.error('Error loading comments:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load comments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchComments(selectedPlatform === 'all' ? 'all' : activeTab);
  }, [fetchComments, selectedPlatform, activeTab]);

  useEffect(() => {
    if (selectedPlatform === 'all') {
      return;
    }
    setActiveTab(selectedPlatform);
  }, [selectedPlatform]);

  useEffect(() => {
    if (selectedPlatform !== 'all') {
      fetchComments(selectedPlatform);
    }
  }, [selectedPlatform, fetchComments]);

  useEffect(() => {
    const currentList = comments[activeTab] || [];
    if (currentList.length === 0) {
      setSelectedThread(null);
      return;
    }

    if (!selectedThread || !currentList.some((item) => item.id === selectedThread.id)) {
      setSelectedThread(currentList[0]);
      setReplyTarget(currentList[0]);
    }
  }, [comments, activeTab, selectedThread]);

  const currentComments = useMemo(() => {
    const list = comments[activeTab] || [];
    if (!search.trim()) return list;
    const lower = search.toLowerCase();
    return list.filter(
      (comment) =>
        comment.username?.toLowerCase().includes(lower) ||
        comment.text?.toLowerCase().includes(lower) ||
        comment.post?.caption?.toLowerCase().includes(lower)
    );
  }, [comments, activeTab, search]);

  const handleSendReply = async () => {
    if (!replyTarget || !replyText.trim()) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      await axios.post(
        `${API}/${activeTab}/comments/${replyTarget.id}/reply`,
        { text: replyText },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      await fetchComments(activeTab);
      setReplyText('');
    } catch (err) {
      console.error('Error sending reply:', err);
    }
  };

  const handleSelectThread = (thread) => {
    setSelectedThread(thread);
    setReplyTarget(thread);
    setReplyText('');
  };

  const handleReplyToMessage = (messageId) => {
    if (!selectedThread) return;
    if (selectedThread.id === messageId) {
      setReplyTarget(selectedThread);
      return;
    }

    const reply = (selectedThread.replies || []).find((item) => item.id === messageId);
    if (reply) {
      setReplyTarget(reply);
    }
  };

  const renderThread = () => {
    if (loading) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="h-10 w-10 rounded-full border-t-2 border-b-2 border-purple-500 animate-spin" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center text-center text-gray-400 px-6">
          <p className="text-sm mb-3">{error}</p>
          <Button variant="ghost" onClick={() => fetchComments(activeTab)}>
            Retry
          </Button>
        </div>
      );
    }

    if (!selectedThread) {
      return (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
          Select a comment to view the conversation
        </div>
      );
    }

    const replies = selectedThread.replies || [];

    return (
      <div className="flex-1 flex flex-col min-h-0">
        <PostPreview post={selectedThread.post} />

        <div className="bg-[#181828] border border-gray-800 rounded-xl p-4 mb-3">
          <div className="flex items-start gap-3">
            <Avatar className="w-10 h-10">
              <img
                src={selectedThread.profile_pic || `https://ui-avatars.com/api/?name=${selectedThread.username}`}
                alt={selectedThread.username}
              />
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-white">{selectedThread.username}</p>
                <span className="text-xs text-gray-500">{formatTimestamp(selectedThread.timestamp)}</span>
              </div>
              <p className="mt-2 text-sm text-gray-200 whitespace-pre-line">{selectedThread.text || 'No comment text provided.'}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1">
          {replies.length === 0 ? (
            <div className="text-center text-xs text-gray-500 py-8">No replies yet.</div>
          ) : (
            replies.map((reply) => (
              <div key={reply.id} className="px-1" onClick={() => handleReplyToMessage(reply.id)}>
                <ThreadMessage
                  username={reply.username}
                  text={reply.text}
                  timestamp={reply.timestamp}
                  align={reply.username === selectedThread.username ? 'left' : 'right'}
                />
              </div>
            ))
          )}
        </div>

        <div className="pt-3 border-t border-gray-800 mt-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400">
              Replying to{' '}
              <span className="text-pink-400">
                {replyTarget?.username || selectedThread.username}
              </span>
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-500 hover:text-gray-300"
              onClick={() => {
                setReplyTarget(selectedThread);
                setReplyText('');
              }}
            >
              Reset
            </Button>
          </div>
          <div className="flex gap-2">
            <Input
              value={replyText}
              onChange={(event) => setReplyText(event.target.value)}
              placeholder="Write a reply..."
              className="bg-[#0f0f1a] border-gray-700 text-white"
            />
            <Button
              onClick={handleSendReply}
              disabled={!replyText.trim()}
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderList = () => (
    <div className="flex flex-col h-full bg-[#1a1a2e] border border-gray-800 rounded-xl">
      <div className="p-4 border-b border-gray-800 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-white flex items-center gap-2">
            {activeTab === 'facebook' ? <Facebook className="h-4 w-4 text-blue-400" /> : <Instagram className="h-4 w-4 text-pink-400" />}
            Recent Comments
          </p>
          <span className="text-xs text-gray-500">{currentComments.length} total</span>
        </div>
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search comments..."
          className="bg-[#0f0f1a] border-gray-700 text-sm text-white"
        />
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {currentComments.length === 0 ? (
            <div className="py-10 text-center text-xs text-gray-500">No comments yet</div>
          ) : (
            currentComments.map((comment) => (
              <CommentListItem
                key={comment.id}
                comment={comment}
                isActive={selectedThread?.id === comment.id}
                onSelect={() => handleSelectThread(comment)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );

  const renderContent = () => (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 h-[calc(100vh-320px)]">
      <div className="lg:col-span-4 h-full min-h-0">{renderList()}</div>
      <div className="lg:col-span-8 h-full min-h-0 bg-[#1a1a2e] border border-gray-800 rounded-xl p-4 flex flex-col">
        {renderThread()}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-3">
      {selectedPlatform === 'all' ? (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="inline-flex bg-[#1a1a2e] border border-gray-800 px-1 py-1 gap-1 justify-start w-max">
            <TabsTrigger value="instagram" className="px-3 py-1.5 text-sm">
              <Instagram className="h-4 w-4 mr-1 text-pink-400" />
              Instagram
            </TabsTrigger>
            <TabsTrigger value="facebook" className="px-3 py-1.5 text-sm">
              <Facebook className="h-4 w-4 mr-1 text-blue-400" />
              Facebook
            </TabsTrigger>
          </TabsList>
          <TabsContent value="instagram">{renderContent()}</TabsContent>
          <TabsContent value="facebook">{renderContent()}</TabsContent>
        </Tabs>
      ) : (
        renderContent()
      )}
    </div>
  );
};

export default SocialComments;
