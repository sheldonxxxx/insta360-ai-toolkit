# Public launch

## Name and positioning

**Insta360 AI Toolkit** · repository slug **`insta360-ai-toolkit`**

**Give your AI agent the full picture.** The name combines the camera brand, the audience and the tool format. It describes an agent skill, executable helpers and a local 360° viewer; the README makes the SDK requirement and current photo-only CLI scope explicit.

[repository.json](../repository.json) is the source for the public name, About description, topics and social-preview path. The source archive uses this repository name. The existing `insta360-sdk` skill invocation and local Docker tag remain stable.

## GitHub About fields

Description:

> Give your AI agent an Insta360 photo workflow: stitching, HDR, FlowState and a local 360° viewer. SDK helpers tested on Mac.

Topics:

```text
insta360  360-photos  panorama  image-stitching  ai-agents
agent-skills  codex  photo-editing  hdr  flowstate  mediasdk  docker  macos  panorama-viewer  webgl
```

Apply these to the repository's About settings. [GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics) connect related projects and make public repositories discoverable through topic searches. Storing this JSON alone does not apply the fields to GitHub.

## Social preview

Upload [social-preview.png](assets/social-preview.png) under the repository's **Settings → Social preview**. It is an original 1280×640 illustration, under 1 MB, with an opaque background and no personal media. The editable source is [hero.svg](assets/hero.svg), also used by the README.

GitHub documents [social-preview requirements and upload steps](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview). The illustration communicates the workflow; it is not a sample panorama or proof of stitching quality. The linked validation reports provide the test evidence.

## Release and announcement copy

Release title:

> Insta360 AI Toolkit v0.1.0 — a 360° photo workflow for your AI agent

Short introduction:

> Give your AI agent an Insta360 photo workflow. Insta360 AI Toolkit combines a reusable agent skill with local Docker helpers for native INSP stitching, HDR, FlowState and output verification, plus a local 360° viewer. Bring your own approved SDK; keep originals unchanged and prepare panoramas for your photo editor. Tested on an Apple Silicon Mac using the Linux SDK in Docker.

Use the actual repository and release links when published. Share where Insta360 developers, 360° photographers and agent-tool builders already discuss relevant workflows, respecting each community's rules. Do not post automatically or claim endorsements, universal platform support, one-click SDK access, or test results beyond the evidence.

## Before announcing

- Set the public name, About description, topics and social preview.
- Verify the README on GitHub in both themes and follow its first-use steps from the released files.
- Attach the source/skill ZIPs and checksums to the versioned release.
- Check the actual public repository and release links, including a signed-out view.
- Use the concise introduction above with those real links.

The repository is being prepared privately. Public visibility, social-preview upload, a versioned release and announcements are separate launch steps. Use verified repository URLs and test results; do not invent download counts, CI-success badges or star counts.
