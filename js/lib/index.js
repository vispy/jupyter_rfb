// Export widget models and views, and the npm package version number.

export {RemoteFrameBufferModel, RemoteFrameBufferView} from './widget';

// export {version} from '../package.json'; -> yarn gives warning:
// Should not import the named export 'version' (reexported as 'version') from default-exporting module (only default export is available soon)

export const version = '0.1.0';  // we just keep the module-version at 0.1.0